"""GitHub Release asset transport for large release-archive objects.

Fase 3 of the R2 -> GitHub migration. The inter-job tag/commit/channel
archive (installers, bundles, receipts) cannot live in the Pages
repository: GitHub Pages sites cap at 1 GB and installer bytes must not
become git objects. Those objects move to GitHub Release assets on this
repository instead; small public files (feeds, channel records, the
Termux APT repo) stay in the Pages worktree via ``scripts.releases.pages``.

One archive release holds every asset for a namespace: the workflow sets
``THOR_ARCHIVE_RELEASE`` (``archive-<tag>`` for tag builds, ``ci-archive``
for commit/channel builds). Asset names are flat, so object keys encode
``/`` as ``__``; keys containing ``__`` are rejected to keep the mapping
reversible. All operations shell out to the ``gh`` CLI (already used by
the release workflow); the runner is injectable so tests never touch the
network.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable

from scripts.releases.pages import file_sha256, relative_artifact_path

__all__ = [
    "ArchiveError",
    "asset_info",
    "asset_name_for",
    "download",
    "ensure_release",
    "get_bytes",
    "key_for_asset_name",
    "put",
    "release_tag",
]

Runner = Callable[..., subprocess.CompletedProcess]


class ArchiveError(ValueError):
    """A GitHub Release asset operation failed or violated immutability."""


def release_tag(explicit: str | None = None) -> str:
    tag = explicit or os.environ.get("THOR_ARCHIVE_RELEASE", "")
    if not tag:
        raise ArchiveError(
            "GitHub archive transport requires THOR_ARCHIVE_RELEASE "
            "(the archive release tag, e.g. archive-<tag> or ci-archive)"
        )
    return tag


def asset_name_for(key: str) -> str:
    relative = relative_artifact_path(key)
    if "__" in relative:
        raise ArchiveError(f"Archive key cannot contain '__': {key}")
    return relative.replace("/", "__")


def key_for_asset_name(name: str) -> str:
    return relative_artifact_path(name.replace("__", "/"))


def _run(runner: Runner, args: list[str]) -> subprocess.CompletedProcess:
    result = runner(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise ArchiveError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result


def ensure_release(tag: str | None = None, *, runner: Runner = subprocess.run) -> str:
    """Create the archive release as a draft when missing; return its tag."""
    name = release_tag(tag)
    view = runner(["gh", "release", "view", name], capture_output=True, text=True)
    if view.returncode == 0:
        return name
    _run(runner, ["release", "create", name, "--draft", "--title", f"CI archive {name}",
                  "--notes", "Release staging archive (Fase 3 R2 migration). Not a product release."])
    return name


def _assets(tag: str, runner: Runner) -> dict[str, dict]:
    result = runner(["gh", "api", f"repos/{{owner}}/{{repo}}/releases/tags/{tag}",
                     "--jq", ".assets"], capture_output=True, text=True)
    if result.returncode != 0:
        if "404" in result.stderr:
            return {}
        raise ArchiveError(f"gh api releases/tags/{tag} failed: {result.stderr.strip()}")
    return {asset["name"]: asset for asset in json.loads(result.stdout or "[]")}


def _digest(asset: dict) -> str | None:
    digest = asset.get("digest") or ""
    return digest.removeprefix("sha256:") if digest.startswith("sha256:") else None


def asset_info(key: str, *, tag: str | None = None,
               runner: Runner = subprocess.run) -> dict | None:
    """Return {"size": int, "sha256": str | None} for one object, or None."""
    asset = _assets(release_tag(tag), runner).get(asset_name_for(key))
    if asset is None:
        return None
    return {"size": asset.get("size"), "sha256": _digest(asset)}


def put(key: str, file: str, *, immutable: bool = False, tag: str | None = None,
        runner: Runner = subprocess.run) -> None:
    """Upload one archive object; identical bytes are an idempotent retry."""
    name = release_tag(tag)
    asset = asset_name_for(key)
    source = Path(file)
    existing = _assets(name, runner).get(asset)
    if existing is not None:
        if _digest(existing) == file_sha256(source):
            return
        if immutable:
            raise ArchiveError(f"Refusing to replace immutable archive object: {key}")
    ensure_release(name, runner=runner)
    # `gh release upload` names the asset after the uploaded file's basename
    # (the part after `#` is only a label), so stage the bytes under the
    # key-encoded asset name first: callers may hand us any local filename
    # (archive_inputs stages every input as "input"), and same-named assets
    # collide under --clobber.
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory) / asset
        shutil.copyfile(source, staged)
        _run(runner, ["release", "upload", name, f"{staged}#{asset}", "--clobber"])
    print(f"OK gh-archive: {key} ({source.stat().st_size} bytes)")


def get_bytes(key: str, *, tag: str | None = None,
              runner: Runner = subprocess.run) -> bytes | None:
    """Return the object bytes, or None when the asset does not exist."""
    name = release_tag(tag)
    asset = asset_name_for(key)
    if asset not in _assets(name, runner):
        return None
    with tempfile.TemporaryDirectory() as directory:
        _run(runner, ["release", "download", name, "--pattern", asset, "--dir", directory])
        downloaded = Path(directory) / asset
        return downloaded.read_bytes() if downloaded.is_file() else None


def download(key: str, path: Path, *, expected_size: int, expected_sha256: str,
             tag: str | None = None, runner: Runner = subprocess.run) -> None:
    """Download one object and verify size + sha256 before landing it."""
    name = release_tag(tag)
    asset = asset_name_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        _run(runner, ["release", "download", name, "--pattern", asset, "--dir", directory])
        downloaded = Path(directory) / asset
        if not downloaded.is_file():
            raise ArchiveError(f"Archive asset missing after download: {key}")
        if downloaded.stat().st_size != expected_size:
            raise ArchiveError(f"Archive size mismatch: {key}")
        if hashlib.sha256(downloaded.read_bytes()).hexdigest() != expected_sha256:
            raise ArchiveError(f"Archive digest mismatch: {key}")
        downloaded.replace(path)
