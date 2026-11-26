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
import threading
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


# put() ensures the release per object; without this cache every pinned
# input costs a `gh release view` API call on top of its upload — hundreds
# per staging run — and exhausts the installation rate limit (face96b7
# push runs, HTTP 403). Keyed by runner identity like _assets_cache so
# injected fakes never share state. The lock is held across view+create:
# put() runs on a thread pool, and two threads racing to create the same
# release would fail the second create.
_ensured_releases: set[tuple[Runner, str]] = set()
_ensured_lock = threading.Lock()


def ensure_release(tag: str | None = None, *, runner: Runner = subprocess.run) -> str:
    """Create the archive release as a draft when missing; return its tag."""
    name = release_tag(tag)
    key = (runner, name)
    with _ensured_lock:
        if key in _ensured_releases:
            return name
        view = runner(["gh", "release", "view", name], capture_output=True, text=True)
        if view.returncode != 0:
            _run(runner, ["release", "create", name, "--draft", "--title", f"CI archive {name}",
                          "--notes", "Release staging archive (Fase 3 R2 migration). Not a product release."])
        _ensured_releases.add(key)
    return name


# One asset listing per (runner, tag) serves a whole staging run: listing
# per object costs several API calls per pinned input — hundreds per run —
# and exhausts the installation rate limit (desktop run #8, HTTP 403).
# Keyed by runner identity so injected fakes never share a listing; put()
# keeps the cached listing current after an upload.
_assets_cache: dict[tuple[Runner, str], dict[str, dict]] = {}
_assets_lock = threading.Lock()


def _assets(tag: str, runner: Runner) -> dict[str, dict]:
    key = (runner, tag)
    with _assets_lock:
        cached = _assets_cache.get(key)
        if cached is None:
            cached = _list_assets(tag, runner)
            _assets_cache[key] = cached
        return dict(cached)


def _list_assets(tag: str, runner: Runner) -> dict[str, dict]:
    result = runner(["gh", "api", f"repos/{{owner}}/{{repo}}/releases/tags/{tag}",
                     "--jq", ".assets"], capture_output=True, text=True)
    if result.returncode == 0:
        return {asset["name"]: asset for asset in json.loads(result.stdout or "[]")}
    if "404" not in result.stderr:
        raise ArchiveError(f"gh api releases/tags/{tag} failed: {result.stderr.strip()}")
    # A draft release has no tag ref yet, so the by-tag endpoint 404s even
    # though the release exists — and every archive release here is a draft.
    # Resolve it through the release list, then read assets by release id;
    # without this, every archived object looks missing and callers fall
    # back to re-downloading from upstream on every run.
    listing = runner(["gh", "api", "repos/{owner}/{repo}/releases?per_page=100"],
                     capture_output=True, text=True)
    if listing.returncode != 0:
        raise ArchiveError(f"gh api releases failed: {listing.stderr.strip()}")
    release_id = next((row["id"] for row in json.loads(listing.stdout or "[]")
                       if row.get("tag_name") == tag), None)
    if release_id is None:
        return {}
    assets: dict[str, dict] = {}
    page = 1
    while True:
        result = runner(["gh", "api",
                         f"repos/{{owner}}/{{repo}}/releases/{release_id}/assets"
                         f"?per_page=100&page={page}"],
                        capture_output=True, text=True)
        if result.returncode != 0:
            raise ArchiveError(
                f"gh api releases/{release_id}/assets failed: {result.stderr.strip()}")
        rows = json.loads(result.stdout or "[]")
        assets.update({asset["name"]: asset for asset in rows})
        if len(rows) < 100:
            return assets
        page += 1


def _digest(asset: dict) -> str | None:
    digest = asset.get("digest") or ""
    return digest.removeprefix("sha256:") if digest.startswith("sha256:") else None


def _landed_by_concurrent_upload(tag: str, asset: str, source: Path,
                                 runner: Runner) -> bool:
    """True when a fresh listing shows `asset` already holding our bytes.

    Bypasses the cached listing on purpose: the cache predates the race
    that just failed our upload, so only a fresh read can see the rival
    job's asset. A failed listing reads as "not landed" so the caller
    falls back to its one retry instead of masking the upload error.
    """
    try:
        fresh = _list_assets(tag, runner)
    except ArchiveError:
        return False
    with _assets_lock:
        if (runner, tag) in _assets_cache:
            _assets_cache[(runner, tag)] = fresh
    rival = fresh.get(asset)
    return rival is not None and _digest(rival) == file_sha256(source)


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
        try:
            _run(runner, ["release", "upload", name, f"{staged}#{asset}", "--clobber"])
        except ArchiveError:
            # A concurrent run's --clobber upload can replace the asset
            # while this upload is in flight (HTTP 404 on the old asset
            # id), or land first and make ours fail with HTTP 422
            # "ReleaseAsset.name already exists". Keys are
            # content-addressed, so check a FRESH listing (the cached one
            # predates the race): if the asset is already there with our
            # digest, the other run landed identical bytes and this put
            # has succeeded. Otherwise one retry re-resolves it by name.
            if not _landed_by_concurrent_upload(name, asset, source, runner):
                _run(runner, ["release", "upload", name, f"{staged}#{asset}", "--clobber"])
    with _assets_lock:
        cached = _assets_cache.get((runner, name))
        if cached is not None:
            cached[asset] = {"name": asset, "size": source.stat().st_size,
                             "digest": "sha256:" + file_sha256(source)}
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
        try:
            _run(runner, ["release", "download", name, "--pattern", asset, "--dir", directory])
        except ArchiveError:
            # A concurrent run's --clobber upload can replace the asset
            # between listing and download (HTTP 404 on the old asset id);
            # one retry re-resolves it by name. Size + sha256 below still
            # bind the bytes that land.
            _run(runner, ["release", "download", name, "--pattern", asset, "--dir", directory])
        downloaded = Path(directory) / asset
        if not downloaded.is_file():
            raise ArchiveError(f"Archive asset missing after download: {key}")
        if downloaded.stat().st_size != expected_size:
            raise ArchiveError(f"Archive size mismatch: {key}")
        if hashlib.sha256(downloaded.read_bytes()).hexdigest() != expected_sha256:
            raise ArchiveError(f"Archive digest mismatch: {key}")
        downloaded.replace(path)
