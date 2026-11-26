"""Validate and conditionally publish macOS update feeds."""
from __future__ import annotations

import re
from typing import Any, Callable

from . import gh_assets, pages
from .semver import compare, is_release_version
from thor_cli.update_channel import canary_timestamp, is_canary_tag

ARCHES = ("arm64",)  # Apple Silicon only: no Intel macOS build ships
_HASH_PATTERN = re.compile(r"^[A-Za-z0-9+/]{86}==$")


def _darwin_feed(channel: str, light: bool = False) -> dict[str, Any]:
    """Legacy URL shape only, not a channel existence registry."""
    if not isinstance(channel, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", channel):
        raise ValueError("Invalid legacy feed path component")
    return {"directory": f"releases/darwin/{'light/' if light else ''}{channel}",
            "channel": channel, "fileName": f"{channel}-mac.yml"}


# ---------------------------------------------------------------------------
# Feed parsing / merging (pure)
# ---------------------------------------------------------------------------

def parse_mac_feed(text: str) -> dict[str, Any]:
    import thor_yaml as yaml  # lazy: YAML support loads only on the feed path

    feed = yaml.safe_load(text)
    if (
        not isinstance(feed, dict)
        or not is_release_version(str(feed.get("version", "")))
        or not isinstance(feed.get("files"), list)
        or not feed["files"]
    ):
        raise ValueError("Invalid macOS update feed")
    for file_entry in feed["files"]:
        if (
            not isinstance(file_entry, dict)
            or not isinstance(file_entry.get("url"), str)
            or not isinstance(file_entry.get("sha512"), str)
            or not _HASH_PATTERN.match(file_entry["sha512"])
            or not isinstance(file_entry.get("size"), int)
            or isinstance(file_entry.get("size"), bool)
            or file_entry["size"] <= 0
        ):
            raise ValueError("Invalid macOS artifact metadata")
    if feed.get("path") and not any(
        isinstance(f, dict)
        and f.get("url") == feed.get("path")
        and f.get("sha512") == feed.get("sha512")
        for f in feed["files"]
    ):
        raise ValueError("Legacy feed path/hash disagrees with files")
    return feed


_MAC_URL_PATTERN = re.compile(
    # Attempt refs (rc.N-vX.Y.Z) key the stable archive; plain and canary
    # vX.Y.Z[+canary...] tags key the rest.
    r"^/releases/tag/(?:v|rc\.[1-9]\d*-v)[0-9A-Za-z.+-]+/[0-9A-Za-z._+-]+\.(zip|dmg)$"
)


def mac_feed_references(text: str) -> list[str]:
    """Every bucket key a published feed references (artifact + .blockmap)."""
    feed = parse_mac_feed(text)
    references: list[str] = []
    for file_entry in feed["files"]:
        # Only our immutable artifact namespace is eligible for publication
        # or pruning; anything else fails loudly instead of half-publishing.
        if not _MAC_URL_PATTERN.match(file_entry["url"]):
            raise ValueError(f"Invalid macOS artifact path: {file_entry['url']}")
        key = file_entry["url"][1:]
        references.extend([key, f"{key}.blockmap"])
    return references


def merge_mac_feeds(legs: dict[str, str], tag: str, light: bool = False,
                    archive: str | None = None) -> dict[str, Any]:
    """Validate the native leg of every ARCHES entry, merge them, and rewrite
    artifact URLs into the immutable per-release tag namespace. `archive` keys
    that namespace (the attempt ref for stable attempts); `tag` stays the
    version identity."""
    import thor_yaml as yaml  # lazy

    version = tag[1:] if isinstance(tag, str) and tag.startswith("v") else ""
    if not is_release_version(version):
        raise ValueError("Invalid macOS release tag")
    selection = _darwin_feed("canary" if is_canary_tag(tag) else "stable", light)
    expected = [f"{arch}-{selection['fileName']}" for arch in ARCHES]
    if sorted(legs.keys()) != sorted(expected):
        raise ValueError("Expected exactly one ARM64 macOS feed")
    files: dict[str, dict[str, Any]] = {}
    first: dict[str, Any] | None = None
    for index, name in enumerate(expected):
        leg = parse_mac_feed(legs[name])
        if str(leg.get("version")) != version:
            raise ValueError(f"Feed version does not match {tag}")
        prefix = f"{'ThorLight' if light else 'ThorBundled'}-{version}-mac-{ARCHES[index]}"
        if not any(f.get("url") == f"{prefix}.zip" for f in leg["files"]):
            raise ValueError(f"Missing native ZIP for {ARCHES[index]}")
        for file_entry in leg["files"]:
            if file_entry.get("url") not in (f"{prefix}.zip", f"{prefix}.dmg"):
                raise ValueError(f"Wrong variant or architecture: {file_entry.get('url')}")
            rewritten = {**file_entry, "url": f"/releases/tag/{archive or tag}/{file_entry['url']}"}
            prior = files.get(file_entry["url"])
            if prior is not None and prior != rewritten:
                raise ValueError(f"Conflicting artifact: {file_entry['url']}")
            files[file_entry["url"]] = rewritten
        if first is None:
            first = leg
    assert first is not None
    merged = {**first, "files": list(files.values())}
    if merged.get("path"):
        merged["path"] = f"/releases/tag/{archive or tag}/{merged['path']}"
    text = yaml.safe_dump(merged, width=100000, default_flow_style=False, sort_keys=False)
    mac_feed_references(text)  # publish only a feed that parses back clean
    return {
        "key": f"{selection['directory']}/{selection['fileName']}",
        "text": text,
        "files": merged["files"],
        "tag": tag,
        "version": version,
    }


# ---------------------------------------------------------------------------
# Publication (transport-verified)
# ---------------------------------------------------------------------------

def publish_mac_feed(
    plan: dict[str, Any],
    transport: dict[str, Callable[..., Any]],
) -> None:
    """The transport verifies immutable bytes and conditionally replaces one
    pointer. Downgrade rejection: semver.compare against the live feed."""
    read = transport["read"]
    verify = transport["verify"]
    write = transport["write"]
    live = read(plan["key"])
    if live:
        old_feed = parse_mac_feed(live["text"])
        next_feed = parse_mac_feed(plan["text"])
        old_url = str(old_feed["files"][0]["url"])
        old_tag = old_url.split("/releases/tag/", 1)[1].split("/", 1)[0]
        old_canary = canary_timestamp(old_tag)
        next_canary = canary_timestamp(plan.get("tag"))
        order = (
            (next_canary > old_canary) - (next_canary < old_canary)
            if next_canary is not None and old_canary is not None
            else compare(plan["version"], str(old_feed["version"]))
        )
        if order < 0:
            raise ValueError("Refusing to move the macOS feed backward")
        if order == 0:
            if old_feed != next_feed:
                raise ValueError("Refusing to replace published version with different artifacts")
            return
    for file_entry in plan["files"]:
        verify(file_entry["url"][1:], file_entry)
    write(plan["key"], plan["text"], live["etag"] if live else None)
    published = read(plan["key"])
    if not published or published["text"] != plan["text"]:
        raise ValueError("macOS feed readback differs from publication")


# ---------------------------------------------------------------------------
# finalize (real signed transport)
# ---------------------------------------------------------------------------

def finalize(tag: str, dir: str, variant: str | None = None, archive: str | None = None,
             verify_bytes: bool = True) -> None:
    """Validate the native legs, verify their archived bytes, then replace
    the feed pointer in the Pages worktree (hash-CAS write, then readback).

    Fase 3 transport split: the feed yml is a small public file and lives
    in the thor-agent-releases Pages worktree (``PAGES_REPO_DIR``); the
    dmg/zip artifacts it points at live in the GitHub archive release
    (``THOR_ARCHIVE_RELEASE``) and are verified through ``gh_assets``.
    ``verify_bytes=False`` (stable promotion of an accepted candidate,
    whose artifacts are already bound by receipt sha256) checks each
    artifact's archived size instead of streaming multi-GB packages back.
    """
    if variant and variant != "light":
        raise ValueError("Unknown macOS variant")
    import os
    import hashlib
    import tempfile
    from pathlib import Path

    worktree = pages.repo_dir_from_env()
    if worktree is None:
        raise ValueError("macOS feed publication requires PAGES_REPO_DIR")

    legs = {
        name: open(os.path.join(dir, name), encoding="utf-8-sig").read()
        for name in sorted(os.listdir(dir))
        if name.endswith("-mac.yml")
    }
    plan = merge_mac_feeds(legs, tag, variant == "light", archive=archive)

    def feed_path(key: str) -> Path:
        scoped = pages.PagesScope.configured().key(key)
        return worktree.joinpath(*scoped.split("/"))

    def read(key: str) -> dict[str, str] | None:
        path = feed_path(key)
        if not path.is_file():
            return None  # first publish: no live feed yet
        body = path.read_bytes()
        return {"text": body.decode("utf-8"), "etag": hashlib.sha256(body).hexdigest()}

    def verify(key: str, file_entry: dict[str, Any]) -> None:
        if not verify_bytes:
            info = gh_assets.asset_info(key)
            if info is None or str(info["size"]) != str(file_entry["size"]):
                raise ValueError(f"Artifact size mismatch: {key}")
            return
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "artifact"
            info = gh_assets.asset_info(key)
            if info is None or not info["sha256"]:
                raise ValueError(f"Artifact missing from archive: {key}")
            gh_assets.download(key, local, expected_size=file_entry["size"],
                               expected_sha256=info["sha256"])
            digest = hashlib.sha512(local.read_bytes()).hexdigest()
            import base64

            if base64.b64encode(bytes.fromhex(digest)).decode() != file_entry["sha512"]:
                raise ValueError(f"Artifact sha512 mismatch: {key}")

    def write(key: str, text: str, etag: str | None) -> None:
        path = feed_path(key)
        current = read(key)
        if etag is not None:
            if current is None or current["etag"] != etag:
                raise ValueError(f"macOS feed changed before write: {key}")
        elif current is not None:
            raise ValueError(f"macOS feed already exists: {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if (worktree / ".git").exists():
            import subprocess

            subprocess.run(["git", "-C", str(worktree), "add", "--",
                            path.relative_to(worktree).as_posix()],
                           check=True, capture_output=True, text=True)

    publish_mac_feed(plan, {"read": read, "verify": verify, "write": write})
    print(f"OK pages: finalized {tag} -> {plan['key']}")

