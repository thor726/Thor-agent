"""GitHub archive transport: keys, immutability, digest-bound downloads."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.releases import gh_assets


class FakeGh:
    """In-memory `gh` stand-in: releases dict tag -> {asset: bytes}."""

    def __init__(self):
        self.releases = {}

    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh"
        cmd = args[1:]
        if cmd[:2] == ["release", "view"]:
            ok = cmd[2] in self.releases
            return subprocess.CompletedProcess(args, 0 if ok else 1, "", "" if ok else "not found")
        if cmd[:2] == ["release", "create"]:
            self.releases.setdefault(cmd[2], {})
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "upload"]:
            tag, spec = cmd[2], cmd[3]
            path, _, asset = spec.partition("#")
            self.releases.setdefault(tag, {})[asset] = open(path, "rb").read()
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "download"]:
            tag = cmd[2]
            asset = cmd[cmd.index("--pattern") + 1]
            directory = cmd[cmd.index("--dir") + 1]
            data = self.releases.get(tag, {}).get(asset)
            if data is None:
                return subprocess.CompletedProcess(args, 1, "", "asset not found")
            open(f"{directory}/{asset}", "wb").write(data)
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:1] == ["api"]:
            tag = cmd[1].rsplit("/", 1)[-1]
            assets = [{"name": name, "size": len(data),
                       "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
                      for name, data in self.releases.get(tag, {}).items()]
            return subprocess.CompletedProcess(args, 0, json.dumps(assets), "")
        raise AssertionError(f"unexpected gh call: {cmd}")


class RecordingGh:
    """Fake `gh` modelling real CLI naming: an uploaded asset takes the
    basename of the file argument; the part after `#` is only its label."""

    def __init__(self):
        self.calls = []
        self.releases = {}  # tag -> {asset name: bytes}

    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh"
        self.calls.append(list(args))
        cmd = args[1:]
        if cmd[:2] == ["release", "view"]:
            ok = cmd[2] in self.releases
            return subprocess.CompletedProcess(args, 0 if ok else 1, "", "" if ok else "not found")
        if cmd[:2] == ["release", "create"]:
            self.releases.setdefault(cmd[2], {})
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "upload"]:
            tag, spec = cmd[2], cmd[3]
            path = spec.partition("#")[0]
            self.releases.setdefault(tag, {})[Path(path).name] = open(path, "rb").read()
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:1] == ["api"]:
            tag = cmd[1].rsplit("/", 1)[-1]
            assets = [{"name": name, "size": len(data),
                       "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
                      for name, data in self.releases.get(tag, {}).items()]
            return subprocess.CompletedProcess(args, 0, json.dumps(assets), "")
        raise AssertionError(f"unexpected gh call: {cmd}")

    def upload_specs(self):
        return [c[4] for c in self.calls if c[1:3] == ["release", "upload"]]


def test_put_uploads_under_key_encoded_name_not_source_basename(tmp_path, monkeypatch):
    # Regression (termux-verify run #17): archive_inputs stages every input
    # to a local file named "input", so uploads named after the source file
    # all collided on the asset name "input".
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RecordingGh()
    source = tmp_path / "input"
    source.write_bytes(b"toolchain bytes")
    key = "upstream/sha256/23871b1702bfd550fb5f901778fd4290ecf2ee034a45a889fbe96d89b188086d"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    (spec,) = gh.upload_specs()
    assert Path(spec.partition("#")[0]).name == gh_assets.asset_name_for(key)
    assert list(gh.releases["ci-archive"]) == [gh_assets.asset_name_for(key)]


def test_put_two_keys_same_source_name_do_not_collide(tmp_path, monkeypatch):
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RecordingGh()
    keys = ["upstream/sha256/aaaa", "upstream/sha256/bbbb"]
    for i, key in enumerate(keys):
        source = tmp_path / f"stage{i}" / "input"
        source.parent.mkdir()
        source.write_bytes(f"bytes {i}".encode())
        gh_assets.put(key, str(source), immutable=True, runner=gh)
    names = [Path(spec.partition("#")[0]).name for spec in gh.upload_specs()]
    assert names == [gh_assets.asset_name_for(k) for k in keys]
    assert set(gh.releases["ci-archive"]) == set(names)


def test_asset_name_roundtrip_and_rejects_ambiguous_keys():
    key = "releases/tag/v1.2.3/ThorBundled-1.2.3-win.msix"
    assert gh_assets.key_for_asset_name(gh_assets.asset_name_for(key)) == key
    with pytest.raises(gh_assets.ArchiveError):
        gh_assets.asset_name_for("releases/tag/v1.2.3/a__b.msix")


def test_put_get_download_and_immutable_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "archive-v1.2.3")
    gh = FakeGh()
    source = tmp_path / "app.msix"
    source.write_bytes(b"package bytes")
    key = "releases/tag/v1.2.3/app.msix"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    gh_assets.put(key, str(source), immutable=True, runner=gh)  # idempotent retry
    assert gh_assets.get_bytes(key, runner=gh) == b"package bytes"
    assert gh_assets.get_bytes("releases/tag/v1.2.3/missing.msix", runner=gh) is None
    target = tmp_path / "out" / "app.msix"
    gh_assets.download(key, target, expected_size=13,
                       expected_sha256=hashlib.sha256(b"package bytes").hexdigest(), runner=gh)
    assert target.read_bytes() == b"package bytes"
    source.write_bytes(b"different bytes")
    with pytest.raises(gh_assets.ArchiveError):
        gh_assets.put(key, str(source), immutable=True, runner=gh)
    with pytest.raises(gh_assets.ArchiveError):
        gh_assets.download(key, target, expected_size=13, expected_sha256="0" * 64, runner=gh)


class DraftGh:
    """Fake `gh` for a DRAFT archive release: the by-tag REST endpoint 404s
    (a draft has no tag ref yet), while the release list and the by-id
    assets endpoint see it. Mirrors the real ci-archive draft."""

    def __init__(self, tag, assets):
        self.tag = tag
        self.assets = assets  # asset name -> bytes
        self.uploads = []

    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh"
        cmd = args[1:]
        if cmd[:2] == ["release", "view"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "upload"]:
            self.uploads.append(cmd[3])
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:1] == ["api"]:
            endpoint = cmd[1]
            if "/releases/tags/" in endpoint:
                return subprocess.CompletedProcess(args, 1, "", "HTTP 404: Not Found")
            if endpoint.rstrip("/").endswith("/releases") or "/releases?" in endpoint:
                listing = [{"id": 42, "tag_name": self.tag, "draft": True}]
                return subprocess.CompletedProcess(args, 0, json.dumps(listing), "")
            if "/releases/42/assets" in endpoint:
                assets = [{"name": name, "size": len(data),
                           "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
                          for name, data in self.assets.items()]
                return subprocess.CompletedProcess(args, 0, json.dumps(assets), "")
        raise AssertionError(f"unexpected gh call: {cmd}")


def test_asset_info_sees_draft_archive_release(tmp_path, monkeypatch):
    # Regression: ci-archive is a draft, so releases/tags/{tag} 404s and
    # asset_info reported every archived input as missing — CI re-downloaded
    # every pin from upstream on every run, and broke the moment the Termux
    # pool retired one (glib 2.90.1, 2026-11-26).
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    key = "upstream/sha256/aaaa"
    gh = DraftGh("ci-archive", {gh_assets.asset_name_for(key): b"pinned bytes"})
    info = gh_assets.asset_info(key, runner=gh)
    assert info == {"size": 12, "sha256": hashlib.sha256(b"pinned bytes").hexdigest()}
    # Identical bytes already archived: put is an idempotent no-op.
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    assert gh.uploads == []
