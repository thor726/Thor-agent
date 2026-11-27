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


def test_asset_listing_is_cached_per_runner(tmp_path, monkeypatch):
    # Regression (desktop run #8, 2026-11-26): every asset_info/put/download
    # re-listed the release's assets — several API calls per pinned input,
    # hundreds per run — until the installation rate limit (HTTP 403) failed
    # the archive step. One listing per (runner, tag) must serve the run.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RecordingGh()
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    assert gh_assets.asset_info(key, runner=gh)["size"] == 12
    assert gh_assets.asset_info(key, runner=gh)["size"] == 12
    api_calls = [c for c in gh.calls if c[1:2] == ["api"]]
    assert len(api_calls) == 1


def test_ensure_release_checks_existence_once_per_runner(tmp_path, monkeypatch):
    # Regression (face96b7 push runs, 2026-11-26): put() called
    # ensure_release per object, and each call ran `gh release view` — one
    # API call per pinned input on top of the listing — until the
    # installation rate limit (HTTP 403) failed the archive step. The
    # existence check must run once per (runner, tag) per process.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RecordingGh()
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    gh_assets.put("upstream/sha256/aaaa", str(source), immutable=True, runner=gh)
    gh_assets.put("upstream/sha256/bbbb", str(source), immutable=True, runner=gh)
    views = [c for c in gh.calls if c[1:3] == ["release", "view"]]
    creates = [c for c in gh.calls if c[1:3] == ["release", "create"]]
    assert len(views) == 1
    assert len(creates) == 1


class FlakyGh:
    """Fake `gh` whose first asset download fails transiently (a concurrent
    run's --clobber upload replaced the asset between listing and download)."""

    def __init__(self, data):
        self.data = data
        self.downloads = 0

    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh"
        cmd = args[1:]
        if cmd[:1] == ["api"]:
            assets = [{"name": "upstream__sha256__aaaa", "size": len(self.data),
                       "digest": "sha256:" + hashlib.sha256(self.data).hexdigest()}]
            return subprocess.CompletedProcess(args, 0, json.dumps(assets), "")
        if cmd[:2] == ["release", "download"]:
            self.downloads += 1
            if self.downloads == 1:
                return subprocess.CompletedProcess(args, 1, "", "HTTP 404: Not Found")
            directory = cmd[cmd.index("--dir") + 1]
            open(f"{directory}/upstream__sha256__aaaa", "wb").write(self.data)
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"unexpected gh call: {cmd}")


def test_download_retries_once_on_transient_failure(tmp_path, monkeypatch):
    # Regression (archive-inputs run #10, 2026-11-26): three runs staging
    # into the same ci-archive release raced — one run's --clobber upload
    # replaced an asset another run was downloading (HTTP 404 on the old
    # asset id). One retry re-resolves the asset by name.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = FlakyGh(b"pinned bytes")
    target = tmp_path / "out"
    gh_assets.download("upstream/sha256/aaaa", target, expected_size=12,
                       expected_sha256=hashlib.sha256(b"pinned bytes").hexdigest(),
                       runner=gh)
    assert target.read_bytes() == b"pinned bytes"
    assert gh.downloads == 2


class FlakyUploadGh(RecordingGh):
    """RecordingGh whose first upload dies the way a lost --clobber race
    does: HTTP 404 on the asset id another run just replaced."""

    def __init__(self):
        super().__init__()
        self.uploads = 0

    def __call__(self, args, capture_output=True, text=True):
        if args[1:3] == ["release", "upload"]:
            self.uploads += 1
            if self.uploads == 1:
                return subprocess.CompletedProcess(
                    args, 1, "", "HTTP 404: Not Found")
        return super().__call__(args, capture_output=capture_output, text=text)


def test_put_retries_once_on_transient_upload_failure(tmp_path, monkeypatch):
    # Regression (stable release v0.23.6 run 45834643789, 2026-11-26): five
    # jobs staged pinned inputs into the same ci-archive release at once;
    # one job's --clobber upload replaced an asset another job was still
    # uploading, and the loser died with HTTP 404 on the old asset id. One
    # retry re-resolves the asset by name; keys are content-addressed, so
    # the retried upload lands identical bytes.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = FlakyUploadGh()
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    assert gh.uploads == 2
    assert gh.releases["ci-archive"] == {gh_assets.asset_name_for(key): b"pinned bytes"}


class RacingUploadGh(RecordingGh):
    """RecordingGh whose first upload loses the race to a concurrent job:
    the rival's upload of the same asset lands first and ours dies with
    HTTP 422 "ReleaseAsset.name already exists". ``rival_bytes`` is what
    the rival landed — identical bytes for content-addressed keys."""

    def __init__(self, rival_bytes):
        super().__init__()
        self.rival_bytes = rival_bytes
        self.uploads = 0

    def __call__(self, args, capture_output=True, text=True):
        if args[1:3] == ["release", "upload"]:
            self.uploads += 1
            if self.uploads == 1:
                tag, spec = args[3], args[4]
                asset = Path(spec.partition("#")[0]).name
                self.releases.setdefault(tag, {})[asset] = self.rival_bytes
                return subprocess.CompletedProcess(
                    args, 1, "", "HTTP 422: ReleaseAsset.name already exists")
        return super().__call__(args, capture_output=capture_output, text=text)


def test_put_treats_existing_same_digest_asset_as_success(tmp_path, monkeypatch):
    # Regression (stable release run, 2026-11-27): many jobs upload the
    # same content-addressed asset into the ci-archive draft at once; the
    # loser's --clobber upload dies with HTTP 422 "already exists" even
    # though the winner landed identical bytes. A fresh listing showing
    # the asset with a matching digest is success — no retry needed.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RacingUploadGh(b"pinned bytes")
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    assert gh.uploads == 1
    assert gh.releases["ci-archive"] == {gh_assets.asset_name_for(key): b"pinned bytes"}


def test_put_retries_when_existing_asset_digest_differs(tmp_path, monkeypatch):
    # Same race, but the asset that landed first is NOT our bytes: the
    # fresh-listing check must not claim success — fall back to the one
    # retry from fix #4 so our bytes land.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RacingUploadGh(b"rival bytes!")
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    gh_assets.put(key, str(source), immutable=True, runner=gh)
    assert gh.uploads == 2
    assert gh.releases["ci-archive"] == {gh_assets.asset_name_for(key): b"pinned bytes"}


class RateLimitedUploadGh(RecordingGh):
    """RecordingGh whose first uploads die on the installation API rate
    limit (HTTP 403), then succeed — the rc.2 stable-release failure."""

    def __init__(self, failures=2):
        super().__init__()
        self.failures = failures
        self.uploads = 0

    def __call__(self, args, capture_output=True, text=True):
        if args[1:3] == ["release", "upload"]:
            self.uploads += 1
            if self.uploads <= self.failures:
                return subprocess.CompletedProcess(
                    args, 1, "", "HTTP 403: API rate limit exceeded for installation")
        return super().__call__(args, capture_output=capture_output, text=text)


def test_put_retries_rate_limit_with_growing_backoff(tmp_path, monkeypatch):
    # Regression (stable release rc.2-v0.23.6, run 46017070348, 2026-11-27):
    # many jobs staging pinned inputs into ci-archive at once exhausted
    # the installation API quota, and every upload died with HTTP 403 —
    # the old code treated it like a lost --clobber race (one fresh-listing
    # check, one retry) and failed. A rate-limit failure must wait and
    # retry with growing backoff instead of failing fast.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = RateLimitedUploadGh(failures=2)
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    delays = []
    gh_assets.put(key, str(source), immutable=True, runner=gh, sleep=delays.append)
    assert gh.uploads == 3
    assert gh.releases["ci-archive"] == {gh_assets.asset_name_for(key): b"pinned bytes"}
    assert len(delays) == 2
    assert delays[0] < delays[1]
    assert 30.0 <= delays[0] <= 60.0
    assert 90.0 <= delays[1] <= 120.0


class Always422UploadGh(RecordingGh):
    """RecordingGh whose uploads always die with HTTP 422 — a rival's
    --clobber upload landed first every time."""

    def __init__(self):
        super().__init__()
        self.uploads = 0

    def __call__(self, args, capture_output=True, text=True):
        if args[1:3] == ["release", "upload"]:
            self.uploads += 1
            return subprocess.CompletedProcess(
                args, 1, "", "HTTP 422: ReleaseAsset.name already exists")
        return super().__call__(args, capture_output=capture_output, text=text)


def test_put_does_not_backoff_on_non_rate_limit_error(tmp_path, monkeypatch):
    # A 422 "already exists" is a lost --clobber race, not a rate limit:
    # it must keep the existing path (fresh listing, then one retry) and
    # still raise — no sleeping, no extra retries.
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    gh = Always422UploadGh()
    source = tmp_path / "input"
    source.write_bytes(b"pinned bytes")
    key = "upstream/sha256/aaaa"
    delays = []
    with pytest.raises(gh_assets.ArchiveError):
        gh_assets.put(key, str(source), immutable=True, runner=gh, sleep=delays.append)
    assert gh.uploads == 2
    assert delays == []
