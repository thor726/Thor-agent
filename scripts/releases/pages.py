"""GitHub Pages release transport: publish into the thor-agent-releases worktree.

The public host is the GitHub Pages site of the
``thor726/thor-agent-releases`` repository; object keys are paths inside
that repository, so ``put`` writes a file into a local checkout
(``PAGES_REPO_DIR``) instead of uploading to an object store. Committing
and pushing that checkout is a separate, explicit step
(``publish_worktree`` / the ``publish`` CLI command) so callers and tests
never touch the network implicitly.

This module also owns the pure release-layout helpers (object keys,
public URLs, artifact-path validation) and the public read path
(receipt-bound downloads from the Pages origin) that every release
caller shares.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Callable, Iterable
from urllib.parse import quote, urlparse

__all__ = [
    "DEFAULT_PUBLIC_URL",
    "PagesChannelStore",
    "PagesScope",
    "PublicFetchError",
    "cache_control_for",
    "channel_for_tag",
    "channel_page_key_for",
    "channel_public_base",
    "commit_key_for",
    "commit_page_key_for",
    "commit_prefix_for",
    "download_public_object",
    "feed_dir_for",
    "file_sha256",
    "is_full_sha",
    "public_artifact_url",
    "public_base_url",
    "public_root_url",
    "public_url_for",
    "publish_worktree",
    "put",
    "read_public_receipt",
    "relative_artifact_path",
    "repo_dir_from_env",
    "require_run",
    "staging_key_for",
    "wait_public_bytes",
]

# The Pages site of thor726/thor-agent-releases is the production origin.
# THOR_PAGES_PUBLIC_URL overrides it (tests, forks).
DEFAULT_PUBLIC_URL = "https://thor726.github.io/thor-agent-releases"


# ---------------------------------------------------------------------------
# Layout helpers (pure)
# ---------------------------------------------------------------------------

def channel_for_tag(tag: str) -> str:
    """Return the release channel encoded by a canonical tag."""
    from thor_cli.update_channel import is_canary_tag

    return "canary" if is_canary_tag(tag) else "stable"


def staging_key_for(tag: str, filename: str) -> str:
    return f"releases/tag/{tag}/{filename}"


_FULL_SHA_RE = re.compile(r"[a-f0-9]{40}")


def is_full_sha(value: str) -> bool:
    return bool(isinstance(value, str) and _FULL_SHA_RE.fullmatch(value))


# Windows reserved names (CPython ntpath parity). COM/LPT superscript forms
# (COM² etc.) are reserved under NTFS namespace rules, same as the digit forms.
_WIN_RESERVED_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"]
    + [f"COM{i}" for i in range(1, 10)] + ["COM¹", "COM²", "COM³"]
    + [f"LPT{i}" for i in range(1, 10)] + ["LPT¹", "LPT²", "LPT³"]
)


def _is_windows_reserved(value: str) -> bool:
    """True if any path component is reserved on Windows.

    Port of ntpath.isreserved() (added in Python 3.13; release CI may run
    older system Pythons, so inline the semantics rather than depend on it).
    """
    for part in reversed(value.split("/")):
        # Trailing dots and spaces are reserved.
        if part[-1:] in (".", " ") and part not in (".", ".."):
            return True
        stem = part.partition(".")[0].rstrip(" ").upper()
        if stem in _WIN_RESERVED_NAMES:
            return True
    return False


def relative_artifact_path(value: str) -> str:
    """Validate the original path before any filesystem normalization."""
    if (not isinstance(value, str) or not value or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(c in value for c in "\\:%?#") or any(ord(c) < 32 for c in value)
            or _is_windows_reserved(value)):
        raise ValueError("Invalid release artifact path")
    return value


def commit_key_for(commit: str, filename: str) -> str:
    """Keep nested artifacts inside the exact commit namespace."""
    return commit_prefix_for(commit) + relative_artifact_path(filename)


def commit_prefix_for(commit: str) -> str:
    if not is_full_sha(commit):
        raise ValueError("Commit builds require an exact full 40-character SHA")
    return f"releases/commit/{commit}/"


def public_url_for(base_url: str, key: str) -> str:
    """Public download URL of an object key (segment-wise encoded)."""
    return f"{base_url.rstrip('/')}/{quote(key, safe='/')}"


def channel_page_key_for(channel: str) -> str:
    """The mutable per-channel downloads page, replaced by each release."""
    return f"releases/{channel}/index.html"


def commit_page_key_for(commit: str) -> str:
    """The per-commit-build downloads page (every expected binary, built or not)."""
    return commit_prefix_for(commit) + "index.html"


def feed_dir_for(platform: str, channel: str) -> str:
    return f"releases/{platform}/{channel}"


def cache_control_for(key: str) -> str | None:
    """APT indexes are mutable; by-hash indexes and versioned packages are not."""
    if key.startswith("releases/channels/"):
        return "no-store"
    if key.startswith(("releases/channel-builds/", "releases/channel-identities/")):
        return "public, max-age=31536000, immutable"
    if key.endswith((".appinstaller", ".html")) or key.startswith("releases/stable/") or (key.startswith("releases/darwin/") and key.endswith("-mac.yml")):
        return "no-store"
    if not key.startswith("releases/termux/"):
        return None
    return (
        "public, max-age=31536000, immutable"
        if "/by-hash/" in key or "/pool/" in key
        else "no-store"
    )


def stream_file(path: str, chunk_size: int = 1024 * 1024) -> Iterable[bytes]:
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    for chunk in stream_file(path):
        digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Public reads (receipt-bound downloads from the Pages origin)
# ---------------------------------------------------------------------------

class PublicFetchError(ValueError):
    """A public-origin GET failed with an HTTP status (404 = missing object)."""

    def __init__(self, method: str, path: str, status: int, body: str = ""):
        self.method, self.path, self.status, self.body = method, path, status, body
        super().__init__(f"Public {method} {path} -> {status}" + (f": {body[:300]}" if body else ""))


def _connection(url: str, timeout: float) -> http.client.HTTPConnection:
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if parsed.scheme == "https":
        import ssl
        return http.client.HTTPSConnection(
            parsed.hostname, port, context=ssl.create_default_context(), timeout=timeout
        )
    return http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)


_RETRYABLE_STATUSES = {500, 502, 503, 504}


def public_artifact_url(base: str, key: str) -> str:
    """Public reads never carry credentials or follow redirects out of the archive."""
    parsed = urlparse(base)
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.params
            or any(c in base for c in ('%', '\\')) or any(ord(c) <= 32 for c in base)
            or any(part in ('.', '..') for part in parsed.path.split('/'))
            or not (parsed.scheme == 'https' or (parsed.scheme == 'http'
                    and parsed.hostname in ('127.0.0.1', 'localhost', '::1')))):
        raise ValueError('Invalid public artifact base URL')
    return public_url_for(base, relative_artifact_path(key))


def read_public_receipt(base: str, key: str) -> dict:
    url = public_artifact_url(base, key)
    parsed = urlparse(url)
    conn = _connection(url, timeout=60.0)
    try:
        conn.request('GET', parsed.path)
        response = conn.getresponse()
        if response.status != 200:
            raise PublicFetchError('GET', parsed.path, response.status)
        # Receipts are metadata, never an unbounded binary download.
        body = response.read(4 * 1024 * 1024 + 1)
        if len(body) > 4 * 1024 * 1024:
            raise ValueError('Public handoff receipt exceeds metadata limit')
        return json.loads(body)
    finally:
        conn.close()


class _TransferMismatch(ValueError):
    """A completed download whose size or SHA256 disagrees with its receipt."""


def download_public_object(base: str, key: str, file: Path, *, expected_size: int, expected_sha256: str) -> None:
    _download_url(public_artifact_url(base, key), file, lambda _attempt: {},
                  expected_size=expected_size, expected_sha256=expected_sha256)


def _download_url(url: str, file: Path, request_headers: Callable[[int], dict[str, str]],
                  *, expected_size: int, expected_sha256: str) -> None:
    """Publish a download locally only after its exact receipt matches."""
    import tempfile

    if type(expected_size) is not int or expected_size < 0 or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("Invalid artifact size or SHA256")
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(url)
    for attempt in range(1, 4):
        conn = _connection(url, timeout=600.0)
        temporary = None
        try:
            conn.request("GET", parsed.path, headers=request_headers(attempt))
            response = conn.getresponse()
            if response.status != 200:
                raise PublicFetchError("GET", parsed.path, response.status)
            digest, size = hashlib.sha256(), 0
            with tempfile.NamedTemporaryFile(dir=file.parent, prefix=f".{file.name}.", delete=False) as output:
                temporary = Path(output.name)
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    if size > expected_size:
                        raise _TransferMismatch(f"Artifact checksum mismatch: {parsed.path}")
                    output.write(chunk)
            if size != expected_size or digest.hexdigest() != expected_sha256:
                raise _TransferMismatch(f"Artifact checksum mismatch: {parsed.path}")
            temporary.replace(file)
            return
        except _TransferMismatch:
            # The receipt is the authority: a body that disagrees with it is a bad transfer, so
            # fetch again; a stored object that really differs fails the same way three times.
            if attempt == 3:
                raise
        except PublicFetchError as error:
            if error.status not in _RETRYABLE_STATUSES or attempt == 3:
                raise
        except (OSError, http.client.HTTPException):
            if attempt == 3:
                raise
        finally:
            conn.close()
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        time.sleep(float(attempt))


_RUN_LEASE = r"[1-9][0-9]{0,19}"


def require_run(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(_RUN_LEASE, value):
        raise ValueError("Disposable Pages run must be <run-id>")
    return value


@dataclass(frozen=True)
class PagesScope:
    """Disposable CI namespace as a path prefix inside the releases repo.

    ``PAGES_DISPOSABLE_RUN`` selects
    ``ci-disposable/<repository-id>/<run-id>/``; unset means production keys.
    """

    prefix: str = ""

    def __post_init__(self):
        if self.prefix and not re.fullmatch(
                r"ci-disposable/[1-9][0-9]{0,19}/" + _RUN_LEASE + r"/", self.prefix):
            raise ValueError("Invalid disposable Pages namespace")

    @classmethod
    def configured(cls, repository: str | None = None) -> "PagesScope":
        run = os.environ.get("PAGES_DISPOSABLE_RUN", "")
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


def wait_public_bytes(url: str, predicate, *, tries: int | None = None,
                      delay_s: float | None = None) -> bytes:
    """Poll a public Pages URL until `predicate(body)` holds.

    A worktree push is not visible until the Pages deploy lands, so every
    public read-back must wait out the deploy lag. Bounded:
    THOR_PAGES_VISIBILITY_TRIES / _DELAY_S override the
    defaults (tests set them to 1 / 0). Raises ValueError on timeout.
    """
    import time
    import urllib.error
    import urllib.request

    if tries is None:
        tries = int(os.environ.get("THOR_PAGES_VISIBILITY_TRIES", "30"))
    if delay_s is None:
        delay_s = float(os.environ.get("THOR_PAGES_VISIBILITY_DELAY_S", "10"))
    last: bytes | None = None
    for attempt in range(max(1, tries)):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                last = response.read()
        except (urllib.error.URLError, OSError):
            last = None
        if last is not None and predicate(last):
            return last
        if attempt + 1 < tries and delay_s:
            time.sleep(delay_s)
    raise ValueError(f"Public Pages object not visible after {tries} tries: {url}")


class PagesChannelStore:
    """Channel records as files in the releases worktree, ETag = body SHA256.

    Implements the get/put/keys protocol ChannelPublisher's CAS flow
    expects: ``put`` with an etag only
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
    """CLI: put one object, publish the worktree, or finalize a macOS feed."""
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
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--tag", required=True)
    finalize_parser.add_argument("--dir", required=True)
    finalize_parser.add_argument("--variant", default=None)
    args = parser.parse_args(argv)
    if args.command == "finalize":
        from scripts.releases import darwin as darwin_module

        darwin_module.finalize(tag=args.tag, dir=args.dir, variant=args.variant)
        return
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
