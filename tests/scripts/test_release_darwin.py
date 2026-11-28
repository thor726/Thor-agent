# tests/scripts/test_release_darwin.py — contract tests for the macOS
# electron-updater feed publication (port of tests-js/darwin-feed.test.mjs).
# Feed merge/validation is pure; publication runs against the fake gh
# archive + a real Pages worktree directory (release_fakes), not a
# fabricated backend.

from __future__ import annotations

import hashlib
import os
import tempfile

import pytest
import thor_yaml as yaml

from scripts.releases import darwin, pages
from scripts.releases.darwin import (
    _darwin_feed,
    mac_feed_references,
    merge_mac_feeds,
    parse_mac_feed,
    publish_mac_feed,
)
from tests.scripts.release_fakes import page_bytes, release_transport


def _inputs(version="0.28.0", light=False):
    channel = "canary" if "+canary." in version else "stable"
    bytes_by_key = {}
    legs = {}
    for i, arch in enumerate(darwin.ARCHES):
        name = f"{'ThorLight' if light else 'ThorBundled'}-{version}-mac-{arch}.zip"
        data = f"test artifact {arch}".encode()
        bytes_by_key[f"releases/tag/v{version}/{name}"] = data
        file_entry = {
            "url": name,
            "size": len(data),
            "sha512": base64_sha512(data),
        }
        legs[f"{arch}-{channel}-mac.yml"] = yaml.safe_dump(
            {
                "version": version,
                "files": [file_entry],
                "path": name,
                "sha512": file_entry["sha512"],
                "releaseDate": f"2026-09-0{i + 1}T00:00:00Z",
                "releaseNotes": "two lines\nof release notes",
            },
            sort_keys=False,
        )
    return legs, bytes_by_key


def base64_sha512(data: bytes) -> str:
    return __import__("base64").b64encode(hashlib.sha512(data).digest()).decode("ascii")


def test_merges_native_legs_and_preserves_release_metadata():
    legs, _bytes = _inputs()
    plan = merge_mac_feeds(legs, "v0.28.0")
    feed = parse_mac_feed(plan["text"])
    assert len(feed["files"]) == len(darwin.ARCHES)
    assert feed["releaseNotes"] == "two lines\nof release notes"
    assert plan["key"] == "releases/darwin/stable/stable-mac.yml"
    assert mac_feed_references(plan["text"]) == [
        ref
        for f in feed["files"]
        for ref in (f["url"][1:], f"{f['url'][1:]}.blockmap")
    ]
    assert pages.cache_control_for(plan["key"]) == "no-store"
    selection = _darwin_feed("canary", True)
    light_legs, _ = _inputs("0.29.0+canary.20260906T000000Z", light=True)
    light_plan = merge_mac_feeds(light_legs, "v0.29.0+canary.20260906T000000Z", light=True)
    assert light_plan["key"] == f"{selection['directory']}/{selection['fileName']}"


@pytest.mark.parametrize(
    "kind", ["missing", "version", "variant", "hash", "legacy", "traversal"]
)
def test_rejects_broken_legs_instead_of_publishing(kind):
    legs, _bytes = _inputs()
    key = "arm64-stable-mac.yml"
    feed = yaml.safe_load(legs[key])
    if kind == "missing":
        del legs[key]
    else:
        if kind == "version":
            feed["version"] = "0.27.0"
        if kind == "variant":
            feed["files"][0]["url"] = feed["files"][0]["url"].replace("ThorBundled", "ThorLight")
        if kind == "hash":
            feed["files"][0]["sha512"] = "invalid"
        if kind == "legacy":
            feed["sha512"] = "wrong"
        if kind == "traversal":
            feed["files"][0]["url"] = "../other.zip"
        legs[key] = yaml.safe_dump(feed, sort_keys=False)
    with pytest.raises(Exception):
        merge_mac_feeds(legs, "v0.28.0")


def test_an_intel_leg_is_refused_because_no_intel_build_ships():
    legs, _bytes = _inputs()
    intel = legs["arm64-stable-mac.yml"].replace("mac-arm64", "mac-x64")
    with pytest.raises(ValueError, match="ARM64"):
        merge_mac_feeds({**legs, "x64-stable-mac.yml": intel}, "v0.28.0")
    with pytest.raises(ValueError, match="ARM64"):
        merge_mac_feeds({"x64-stable-mac.yml": intel}, "v0.28.0")


def test_semver_grammar_rejects_non_release_versions():
    # The Python port never imports npm semver; it implements exactly the
    # release grammar (vMAJOR.MINOR.PATCH[+canary.<full UTC timestamp>]) and fails
    # loudly on anything else instead of guessing an order.
    from scripts.releases.semver import compare, is_valid_version

    assert is_valid_version("0.28.0") and is_valid_version("0.28.0+canary.20260904T101010Z")
    # Legacy CalVer (four-digit major) is not a release version anywhere.
    assert not is_valid_version("0.28") and not is_valid_version("2026.7.20")
    assert not is_valid_version("0.28.0-beta.1")
    assert compare("0.28.0", "0.27.9") == 1
    assert compare("0.28.0+canary.20260904T101010Z", "0.28.0") == 0
    assert compare("0.28.0+canary.20260904T101010Z", "0.28.0+canary.20260904T101011Z") == 0
    with pytest.raises(ValueError):
        compare("nonsense", "0.28.0")


def test_finalize_verifies_archive_bytes_and_publishes_last(release_transport):
    gh, worktree = release_transport.gh, release_transport.worktree
    with tempfile.TemporaryDirectory() as dir_path:
        legs, bytes_by_key = _inputs()
        for name, text in legs.items():
            with open(os.path.join(dir_path, name), "w", encoding="utf-8") as handle:
                handle.write(text)
        for key, value in bytes_by_key.items():
            gh.put_bytes(key, value)
        darwin.finalize(tag="v0.28.0", dir=dir_path)
    feed_key = "releases/darwin/stable/stable-mac.yml"
    published = page_bytes(worktree, feed_key).decode("utf-8")
    assert len(parse_mac_feed(published)["files"]) == len(darwin.ARCHES)
    # Every artifact was verified through the archive before the pointer
    # landed in the worktree.
    assert set(gh.downloads()) == set(bytes_by_key)


def test_finalize_rejects_a_downgrade_over_the_live_feed(release_transport):
    gh, worktree = release_transport.gh, release_transport.worktree
    with tempfile.TemporaryDirectory() as dir_path:
        legs, bytes_by_key = _inputs("0.27.0")
        for name, text in legs.items():
            with open(os.path.join(dir_path, name), "w", encoding="utf-8") as handle:
                handle.write(text)
        for key, value in bytes_by_key.items():
            gh.put_bytes(key, value)
        # The live feed is already at 0.28.0.
        newer = merge_mac_feeds(_inputs()[0], "v0.28.0")
        live_path = worktree / "releases/darwin/stable/stable-mac.yml"
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text(newer["text"], encoding="utf-8")
        with pytest.raises(ValueError, match="backward"):
            darwin.finalize(tag="v0.27.0", dir=dir_path)
    # The live pointer was not replaced.
    assert parse_mac_feed(page_bytes(worktree, "releases/darwin/stable/stable-mac.yml").decode())["version"] == "0.28.0"


def test_finalize_rejects_unknown_variant():
    with pytest.raises(ValueError, match="variant"):
        darwin.finalize(tag="v0.28.0", dir=".", variant="dark")


def test_publish_mac_feed_readback_must_match_the_publication():
    plan = merge_mac_feeds(_inputs()[0], "v0.28.0")
    stored = {}

    def write(key, text, etag):
        stored[key] = {"text": text + "# corrupted\n", "etag": "x"}

    with pytest.raises(ValueError, match="readback differs"):
        publish_mac_feed(plan, {"read": stored.get, "verify": lambda key, entry: None, "write": write})


@pytest.mark.parametrize('fault', ['identical', 'different', 'corrupt-artifact', 'missing-artifact', 'raced-feed', 'upgrade'])
def test_finalize_live_feed_faults(tmp_path, release_transport, monkeypatch, fault):
    from scripts.releases import gh_assets

    gh, worktree = release_transport.gh, release_transport.worktree
    legs, content = _inputs()
    for name, text in legs.items():
        (tmp_path / name).write_text(text, encoding='utf-8')
    for key, value in content.items():
        gh.put_bytes(key, value)
    key = 'releases/darwin/stable/stable-mac.yml'
    live = merge_mac_feeds(_inputs('0.28.0' if fault in {'identical', 'different'} else '0.27.0')[0],
                           'v0.28.0' if fault in {'identical', 'different'} else 'v0.27.0')['text']
    if fault == 'different':
        live = live.replace('two lines', 'other notes')
    live_path = worktree.joinpath(*key.split("/"))
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text(live, encoding="utf-8")
    if fault == 'corrupt-artifact':
        first = next(iter(content))
        gh.put_bytes(first, b'x' * len(content[first]))
    if fault == 'missing-artifact':
        gh.delete(next(iter(content)))
    if fault == 'raced-feed':
        original = gh_assets.download
        def race(*args, **kwargs):
            result = original(*args, **kwargs)
            live_path.write_text(live + "# raced\n", encoding="utf-8")
            return result
        monkeypatch.setattr(gh_assets, "download", race)
    errors = {'different': 'different artifacts',
              'corrupt-artifact': 'sha512 mismatch',
              'missing-artifact': 'missing from archive',
              'raced-feed': 'changed before write'}
    if fault in errors:
        with pytest.raises(ValueError, match=errors[fault]):
            darwin.finalize(tag='v0.28.0', dir=str(tmp_path))
    else:
        darwin.finalize(tag='v0.28.0', dir=str(tmp_path))
    if fault in {'identical', 'different', 'corrupt-artifact', 'missing-artifact'}:
        assert page_bytes(worktree, key) == live.encode()
        assert gh.downloads() == [] or fault in {'corrupt-artifact', 'missing-artifact'}
    elif fault == 'raced-feed':
        assert page_bytes(worktree, key) == (live + "# raced\n").encode()
    elif fault == 'upgrade':
        assert parse_mac_feed(page_bytes(worktree, key).decode())['version'] == '0.28.0'
