"""GitHub archive transport: keys, immutability, digest-bound downloads."""
import hashlib
import json
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
