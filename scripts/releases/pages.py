"""GitHub Pages release transport: publish into the thor-agent-releases worktree.

Fase 2 of the R2 -> GitHub migration. The public host is the GitHub Pages
site of the ``thor726/thor-agent-releases`` repository; object keys are
paths inside that repository, so ``put`` writes a file into a local
checkout (``PAGES_REPO_DIR``) instead of uploading to an object store.
Committing and pushing that checkout is a separate, explicit step
(``publish_worktree`` / the ``publish`` CLI command) so callers and tests
never touch the network implicitly.

Transitional fallback: while Fase 3 workflow changes are pending, ``put``
delegates to the R2 transport when no Pages worktree is configured but the
legacy R2 credentials are. Callers no longer import ``scripts.releases.r2``
directly; removing the delegation is a Fase 3 follow-up once every
workflow sets ``PAGES_REPO_DIR``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess

from scripts.releases.r2 import (
    cache_control_for,
    channel_page_key_for,
    commit_page_key_for,
    commit_prefix_for,
    download_public_object,
    feed_dir_for,
    file_sha256,
    public_artifact_url,
    public_url_for,
    relative_artifact_path,
    staging_key_for,
)

__all__ = [
    "DEFAULT_PUBLIC_URL",
    "PagesChannelStore",
    "PagesScope",
    "cache_control_for",
    "channel_page_key_for",
    "channel_public_base",
    "commit_page_key_for",
    "commit_prefix_for",
    "download_public_object",
    "feed_dir_for",
    "file_sha256",
    "public_artifact_url",
    "public_base_url",
    "public_root_url",
    "public_url_for",
    "publish_worktree",
    "put",
    "relative_artifact_path",
    "repo_dir_from_env",
    "require_run",
    "staging_key_for",
]

# The Pages site of thor726/thor-agent-releases is the production origin.
# THOR_PAGES_PUBLIC_URL overrides it (tests, forks); the legacy
# CLOUDFLARE_R2_PUBLIC_URL is still honored during the transition so
# unmigrated workflows keep naming the origin they actually serve.
DEFAULT_PUBLIC_URL = "https://thor726.github.io/thor-agent-releases"

_RUN_LEASE = r"[1-9][0-9]{0,19}"


def require_run(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(_RUN_LEASE, value):
        raise ValueError("Disposable Pages run must be <run-id>")
    return value


@dataclass(frozen=True)
class PagesScope:
    """Disposable CI namespace as a path prefix inside the releases repo.

    Mirrors the old R2 disposable scoping: ``PAGES_DISPOSABLE_RUN`` (or the
    legacy ``R2_DISPOSABLE_RUN`` while workflows migrate) selects
    ``ci-disposable/<repository-id>/<run-id>/``; unset means production keys.
    """

    prefix: str = ""

    def __post_init__(self):
        if self.prefix and not re.fullmatch(
                r"ci-disposable/[1-9][0-9]{0,19}/" + _RUN_LEASE + r"/", self.prefix):
            raise ValueError("Invalid disposable Pages namespace")

    @classmethod
    def configured(cls, repository: str | None = None) -> "PagesScope":
        run = os.environ.get("PAGES_DISPOSABLE_RUN") or os.environ.get("R2_DISPOSABLE_RUN", "")
        if not run:
            return cls()
        require_run(run)
        repository_id = os.environ.get("GITHUB_REPOSITORY_ID", "")
        if not re.fullmatch(r"[1-9][0-9]{0,19}", repository_id):
            raise ValueError("Disposable Pages scope requires the GitHub repository ID")
        return cls(f"ci-disposable/{repository_id}/{run}/")

    def key(self, key: str) -> str:
        if not self.prefix:
            return key
        return self.prefix + relative_artifact_path(key)

    def listing_prefix(self, prefix: str) -> str:
        if not prefix:
            return self.prefix
        return self.key(prefix.removesuffix("/")) + ("/" if prefix.endswith("/") else "")

    def logical_key(self, key: str) -> str:
        if not key.startswith(self.prefix):
            raise ValueError("Pages listing escaped the disposable namespace")
        return key[len(self.prefix):]

    def public_base(self, base: str) -> str:
        root = base.rstrip("/")
        if self.prefix:
            public_artifact_url(root, "scope-check")
            if "/ci-disposable/" in root + "/":
                raise ValueError("Configured Pages public root must not contain a disposable namespace")
            return root + "/" + self.prefix.rstrip("/")
        return root


def public_root_url(explicit: str | None = None) -> str:
    """The unscoped public origin (no disposable prefix)."""
    from thor_cli.release_channels import public_base

    return public_base(
        explicit
        or os.environ.get("THOR_PAGES_PUBLIC_URL")
        or os.environ.get("CLOUDFLARE_R2_PUBLIC_URL")
        or DEFAULT_PUBLIC_URL
    )


def public_base_url(explicit: str | None = None) -> str:
    """The public origin callers read from, disposable scope applied."""
    return PagesScope.configured().public_base(public_root_url(explicit))


def channel_public_base(explicit: str | None = None) -> str:
    """The channel authority for this process, disposable scope applied.

    In a disposable run the explicit value, when given, must already name
    the scoped authority — callers cannot substitute a production-looking
    URL for scoped objects.
    """
    scope = PagesScope.configured()
    if scope.prefix:
        expected = scope.public_base(public_root_url())
        if explicit is not None and explicit.rstrip("/") != expected:
            raise ValueError("Disposable channel archive authority mismatch")
        return expected
    return public_root_url(explicit)


def repo_dir_from_env(explicit: str | Path | None = None) -> Path | None:
    value = explicit or os.environ.get("PAGES_REPO_DIR") or ""
    return Path(value) if value else None


def _worktree_target(repo_dir: Path, key: str) -> Path:
    relative = relative_artifact_path(key)
    target = repo_dir.joinpath(*relative.split("/"))
    if not target.resolve().is_relative_to(repo_dir.resolve()):
        raise ValueError("Invalid release artifact path")
    return target


def put(
    tag: str,
    key: str,
    file: str,
    key_is_full: bool = False,
    immutable: bool = False,
    *,
    repo_dir: str | Path | None = None,
) -> None:
    """Publish one artifact into the Pages worktree.

    `key` is a filename archived under releases/tag/<tag>/ unless
    `key_is_full`. `immutable=True` refuses to replace existing bytes
    (identical bytes are an idempotent retry). The file is written and,
    when the worktree is a git checkout, staged; committing and pushing
    stay explicit via `publish_worktree`.
    """
    worktree = repo_dir_from_env(repo_dir)
    if worktree is None:
        # Transitional fallback (see module docstring): unmigrated callers
        # and tests still configured for R2 keep their transport until
        # Fase 3 sets PAGES_REPO_DIR everywhere.
        if os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID"):
            from scripts.releases import r2

            r2.put(tag=tag, key=key, file=file, key_is_full=key_is_full, immutable=immutable)
            return
        raise ValueError(
            "Pages publishing requires PAGES_REPO_DIR (a thor-agent-releases checkout)"
        )
    key_path = key if key_is_full else staging_key_for(tag, key)
    scoped_key = PagesScope.configured().key(key_path)
    target = _worktree_target(worktree, scoped_key)
    source = Path(file)
    if target.exists():
        if file_sha256(target) == file_sha256(source):
            return
        if immutable:
            raise ValueError(f"Refusing to replace immutable Pages object: {key_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if (worktree / ".git").exists():
        subprocess.run(["git", "-C", str(worktree), "add", "--", scoped_key],
                       check=True, capture_output=True, text=True)
    from scripts.releases.upload_summary import note

    note(key_path)
    print(f"OK pages: {key_path} ({target.stat().st_size} bytes)")


def publish_worktree(repo_dir: str | Path, message: str, *, push: bool = False) -> str | None:
    """Commit staged worktree changes; push only when explicitly asked.

    Returns the new commit SHA, or None when nothing was staged.
    """
    worktree = Path(repo_dir)
    staged = subprocess.run(["git", "-C", str(worktree), "diff", "--cached", "--quiet"],
                            capture_output=True, text=True)
    if staged.returncode == 0:
        return None
    subprocess.run(["git", "-C", str(worktree), "commit", "-m", message],
                   check=True, capture_output=True, text=True)
    if push:
        subprocess.run(["git", "-C", str(worktree), "push"],
                       check=True, capture_output=True, text=True)
    return subprocess.run(["git", "-C", str(worktree), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


class PagesChannelStore:
    """Channel records as files in the releases worktree, ETag = body SHA256.

    Implements the same get/put/keys protocol as the old R2 store so
    ChannelPublisher's CAS flow is unchanged: ``put`` with an etag only
    lands when the current bytes hash to it, and ``put`` without one is
    create-only (identical bytes are an idempotent retry).
    """

    def __init__(self, repo_dir: str | Path, *, scope: PagesScope | None = None):
        self.repo_dir = Path(repo_dir)
        self.scope = PagesScope.configured() if scope is None else scope

    def _path(self, key: str) -> Path:
        from thor_cli.release_channels import artifact_key

        return _worktree_target(self.repo_dir, self.scope.key(artifact_key(key)))

    def get(self, key: str) -> tuple[bytes, str] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        body = path.read_bytes()
        if len(body) > 4 * 1024 * 1024:
            from thor_cli.release_channels import ChannelError

            raise ChannelError("Channel metadata exceeds size limit")
        return body, hashlib.sha256(body).hexdigest()

    def put(self, key: str, body: bytes, etag: str | None = None) -> None:
        from scripts.releases.channels import ChannelConflict

        path = self._path(key)
        current = self.get(key)
        if current is not None and current[0] == body:
            return
        if etag is not None:
            if current is None or current[1] != etag:
                raise ChannelConflict(f"Channel write conflict: {key}")
        elif current is not None:
            raise ChannelConflict(f"Channel write conflict: {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        readback = self.get(key)
        if readback is None or readback[0] != body:
            raise ChannelConflict(f"Channel changed before worktree readback: {key}")
        if (self.repo_dir / ".git").exists():
            subprocess.run(["git", "-C", str(self.repo_dir), "add", "--",
                            path.relative_to(self.repo_dir).as_posix()],
                           check=True, capture_output=True, text=True)
        from scripts.releases.upload_summary import note

        note(self.scope.key(key))

    def keys(self, prefix: str) -> list[str]:
        root = self.repo_dir.joinpath(*self.scope.listing_prefix(prefix).rstrip("/").split("/"))
        if not root.is_dir():
            return []
        return sorted(
            self.scope.logical_key(path.relative_to(self.repo_dir).as_posix())
            for path in root.rglob("*") if path.is_file()
        )


def main(argv: list[str] | None = None) -> None:
    """CLI mirroring the old r2 put surface for Fase 3 workflow swaps."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    put_parser = sub.add_parser("put")
    put_parser.add_argument("--tag", default="")
    put_parser.add_argument("--key", required=True)
    put_parser.add_argument("--file", required=True)
    put_parser.add_argument("--key-is-full", action="store_true")
    put_parser.add_argument("--immutable", action="store_true")
    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("--message", required=True)
    publish_parser.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "put":
        put(tag=args.tag, key=args.key, file=args.file,
            key_is_full=args.key_is_full, immutable=args.immutable)
        return
    worktree = repo_dir_from_env()
    if worktree is None:
        raise SystemExit("::error::PAGES_REPO_DIR is required to publish the Pages worktree")
    publish_worktree(worktree, args.message, push=args.push)


if __name__ == "__main__":
    main()
