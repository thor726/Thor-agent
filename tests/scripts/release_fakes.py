"""Shared fakes for the GitHub-native release transports (Pages + gh archive).

Replaces the retired R2 loopback server: handoff/archive objects live in a
disk-backed fake ``gh`` (``DiskFakeGh``), public files live in a Pages
worktree directory, and a loopback HTTP origin serves both by object key
for public-base reads. No network beyond 127.0.0.1 is touched.
"""
from __future__ import annotations

from collections.abc import MutableMapping
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

import pytest

from scripts.releases import gh_assets


class DiskFakeGh:
    """In-memory-on-disk `gh` stand-in: state_dir/<tag>/<asset> files.

    Implements the exact `gh` surface scripts.releases.gh_assets uses
    (release view/create/upload/download + api releases/tags), naming
    uploaded assets after the uploaded file's basename like the real CLI.
    """

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.calls: list[list[str]] = []

    # -- test-side helpers -------------------------------------------------
    def put_bytes(self, key: str, data: bytes, tag: str = "ci-archive") -> None:
        asset = gh_assets.asset_name_for(key)
        path = self.state_dir / tag / asset
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_bytes(self, key: str, tag: str = "ci-archive") -> bytes | None:
        path = self.state_dir / tag / gh_assets.asset_name_for(key)
        return path.read_bytes() if path.is_file() else None

    def find_bytes(self, key: str) -> bytes | None:
        """Bytes for `key` in any archive release (public-origin lookup)."""
        asset = gh_assets.asset_name_for(key)
        for tag_dir in sorted(self.state_dir.iterdir()) if self.state_dir.is_dir() else []:
            path = tag_dir / asset
            if path.is_file():
                return path.read_bytes()
        return None

    def keys(self, tag: str = "ci-archive") -> list[str]:
        tag_dir = self.state_dir / tag
        if not tag_dir.is_dir():
            return []
        return sorted(gh_assets.key_for_asset_name(p.name) for p in tag_dir.iterdir() if p.is_file())

    def all_keys(self) -> list[str]:
        out = []
        if self.state_dir.is_dir():
            for tag_dir in sorted(self.state_dir.iterdir()):
                out.extend(self.keys(tag_dir.name))
        return sorted(out)

    def delete(self, key: str, tag: str = "ci-archive") -> None:
        (self.state_dir / tag / gh_assets.asset_name_for(key)).unlink(missing_ok=True)

    def uploads(self) -> list[str]:
        """Object keys uploaded through the gh surface, in call order."""
        return [gh_assets.key_for_asset_name(Path(c[4].partition("#")[0]).name)
                for c in self.calls if c[1:3] == ["release", "upload"]]

    def downloads(self) -> list[str]:
        """Object keys downloaded through the gh surface, in call order."""
        return [gh_assets.key_for_asset_name(c[c.index("--pattern") + 1])
                for c in self.calls if c[1:3] == ["release", "download"]]

    # -- gh CLI surface ----------------------------------------------------
    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh", args
        self.calls.append(list(args))
        cmd = args[1:]
        if cmd[:2] == ["release", "view"]:
            ok = (self.state_dir / cmd[2]).is_dir()
            return subprocess.CompletedProcess(args, 0 if ok else 1, "", "" if ok else "not found")
        if cmd[:2] == ["release", "create"]:
            (self.state_dir / cmd[2]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "upload"]:
            tag, spec = cmd[2], cmd[3]
            path = spec.partition("#")[0]
            target = self.state_dir / tag / Path(path).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(path).read_bytes())
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:2] == ["release", "download"]:
            tag = cmd[2]
            asset = cmd[cmd.index("--pattern") + 1]
            directory = cmd[cmd.index("--dir") + 1]
            source = self.state_dir / tag / asset
            if not source.is_file():
                return subprocess.CompletedProcess(args, 1, "", "asset not found")
            Path(directory, asset).write_bytes(source.read_bytes())
            return subprocess.CompletedProcess(args, 0, "", "")
        if cmd[:1] == ["api"]:
            tag = cmd[1].rsplit("/", 1)[-1]
            tag_dir = self.state_dir / tag
            assets = [{"name": p.name, "size": p.stat().st_size,
                       "digest": "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(tag_dir.iterdir()) if p.is_file()] if tag_dir.is_dir() else []
            return subprocess.CompletedProcess(args, 0, json.dumps(assets), "")
        raise AssertionError(f"unexpected gh call: {cmd}")


def install_fake_gh(monkeypatch, state_dir: Path) -> DiskFakeGh:
    """Point scripts.releases.gh_assets at a DiskFakeGh for this process."""
    fake = DiskFakeGh(state_dir)
    originals = {name: getattr(gh_assets, name)
                 for name in ("put", "get_bytes", "download", "asset_info", "ensure_release")}
    monkeypatch.setattr(gh_assets, "put",
                        lambda key, file, **kw: originals["put"](key, file, runner=fake, **kw))
    monkeypatch.setattr(gh_assets, "get_bytes",
                        lambda key, **kw: originals["get_bytes"](key, runner=fake, **kw))
    monkeypatch.setattr(gh_assets, "download",
                        lambda key, path, **kw: originals["download"](key, path, runner=fake, **kw))
    monkeypatch.setattr(gh_assets, "asset_info",
                        lambda key, **kw: originals["asset_info"](key, runner=fake, **kw))
    def _ensure(tag=None, **kw):
        kw.pop("runner", None)
        return originals["ensure_release"](tag, runner=fake, **kw)
    monkeypatch.setattr(gh_assets, "ensure_release", _ensure)
    return fake


def install_fake_gh_driver() -> DiskFakeGh:
    """Subprocess-driver entry: install the fake from $THOR_FAKE_GH_STATE.

    Workflow-step subprocesses (python-driver.py) call this before runpy so
    handoff/archive code in the child talks to the same on-disk archive the
    test process inspects.
    """
    import scripts.releases.gh_assets as module

    fake = DiskFakeGh(Path(os.environ["THOR_FAKE_GH_STATE"]))
    originals = {name: getattr(module, name)
                 for name in ("put", "get_bytes", "download", "asset_info", "ensure_release")}
    module.put = lambda key, file, **kw: originals["put"](key, file, runner=fake, **kw)
    module.get_bytes = lambda key, **kw: originals["get_bytes"](key, runner=fake, **kw)
    module.download = lambda key, path, **kw: originals["download"](key, path, runner=fake, **kw)
    module.asset_info = lambda key, **kw: originals["asset_info"](key, runner=fake, **kw)
    def _ensure(tag=None, **kw):
        kw.pop("runner", None)
        return originals["ensure_release"](tag, runner=fake, **kw)
    module.ensure_release = _ensure
    return fake


class PublicOrigin:
    """Loopback HTTP origin serving Pages-worktree files and archive assets.

    URL shape matches the retired R2 fixture: ``<base>/<key>`` where base is
    ``http://127.0.0.1:<port>/thor-releases``. Lookup order: seeded objects,
    then worktree files, then archive assets in any release.
    """

    def __init__(self, worktree: Path | None = None, gh_state: Path | None = None):
        self.worktree = Path(worktree) if worktree else None
        self.gh = DiskFakeGh(gh_state) if gh_state else None
        self.seeded: dict[str, bytes] = {}
        # When set, every public read returns these bytes (stale CDN model).
        self.stale_all: bytes | None = None
        self.requests: list[tuple[str, str, dict]] = []
        origin = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                origin.requests.append(("GET", self.path, dict(self.headers)))
                key = unquote(urlsplit(self.path).path).lstrip("/")
                if key.startswith("thor-releases/"):
                    key = key[len("thor-releases/"):]
                body = origin.lookup(key)
                if body is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server_port = self.server.server_port
        self.base = f"http://127.0.0.1:{self.server_port}/thor-releases"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def lookup(self, key: str) -> bytes | None:
        if self.stale_all is not None:
            return self.stale_all
        # A disposable-scope public base prefixes keys with
        # ci-disposable/<repo-id>/<run>/; the same bytes live unscoped in
        # the archive, so fall back to the stripped key.
        candidates = [key]
        parts = key.split("/")
        if len(parts) > 3 and parts[0] == "ci-disposable":
            candidates.append("/".join(parts[3:]))
        for candidate in candidates:
            if candidate in self.seeded:
                return self.seeded[candidate]
            if self.worktree is not None:
                path = self.worktree.joinpath(*candidate.split("/"))
                if path.is_file():
                    return path.read_bytes()
            if self.gh is not None:
                data = self.gh.find_bytes(candidate)
                if data is not None:
                    return data
        return None

    def seed(self, key: str, data: bytes) -> None:
        self.seeded[key] = data

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)


def init_pages_worktree(tmp_path: Path) -> Path:
    """A thor-agent-releases checkout backed by a local bare remote.

    ChannelPublisher._write commits and pushes the worktree, so tests that
    drive it need a real git repo with an upstream.
    """
    remote = tmp_path / "pages-remote.git"
    worktree = tmp_path / "pages-host"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "--quiet", str(remote), str(worktree)], check=True, capture_output=True)
    for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid")):
        subprocess.run(["git", "-C", str(worktree), "config", key, value], check=True, capture_output=True)
    (worktree / "README.md").write_text("fixture Pages host\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(worktree), "commit", "--quiet", "-m", "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(worktree), "push", "--quiet", "-u", "origin", "HEAD"],
                   check=True, capture_output=True)
    return worktree


class TransportStore(MutableMapping):
    """(bytes, etag) mapping over worktree files + gh archive assets.

    Keys are literal object keys: reads check the worktree file first,
    then any archive release; writes land as worktree files (the public
    home), deletes clear both. Iteration covers both homes.
    """

    def __init__(self, transport):
        self.transport = transport

    def _path(self, key: str) -> Path:
        return self.transport.worktree.joinpath(*key.split("/"))

    def _candidates(self, key: str) -> list[str]:
        parts = key.split("/")
        if len(parts) > 3 and parts[0] == "ci-disposable":
            return [key, "/".join(parts[3:])]
        return [key]

    def __getitem__(self, key):
        for candidate in self._candidates(key):
            path = self._path(candidate)
            if path.is_file():
                return path.read_bytes(), '"e"'
            data = self.transport.gh.find_bytes(candidate)
            if data is not None:
                return data, '"e"'
        raise KeyError(key)

    def __setitem__(self, key, value):
        data = value[0] if isinstance(value, tuple) else value
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def __delitem__(self, key):
        existed = False
        for candidate in self._candidates(key):
            path = self._path(candidate)
            existed = existed or path.is_file() or self.transport.gh.find_bytes(candidate) is not None
            path.unlink(missing_ok=True)
            self.transport.gh.delete(candidate)
        if not existed:
            raise KeyError(key)

    def __iter__(self):
        # README.md is the fixture worktree's init commit, not a release object.
        keys = {key for key in page_keys(self.transport.worktree) if key != "README.md"}
        return iter(sorted(keys | set(self.transport.gh.all_keys())))

    def __len__(self):
        return sum(1 for _ in self)


def page_bytes(worktree: Path, key: str) -> bytes | None:
    path = Path(worktree).joinpath(*key.split("/"))
    return path.read_bytes() if path.is_file() else None


def page_keys(worktree: Path) -> list[str]:
    root = Path(worktree)
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and ".git/" not in p.relative_to(root).as_posix() + "/")


@pytest.fixture
def release_transport(tmp_path, monkeypatch):
    """Fake gh archive + Pages worktree + public origin, wired by env.

    Returns a namespace: .gh (DiskFakeGh), .gh_state, .worktree, .origin,
    .base (public base URL), .env (extra env for subprocess steps).
    """
    from types import SimpleNamespace

    gh_state = tmp_path / "gh-state"
    fake = install_fake_gh(monkeypatch, gh_state)
    worktree = init_pages_worktree(tmp_path)
    origin = PublicOrigin(worktree=worktree, gh_state=gh_state)
    monkeypatch.setenv("THOR_ARCHIVE_RELEASE", "ci-archive")
    monkeypatch.setenv("PAGES_REPO_DIR", str(worktree))
    monkeypatch.setenv("THOR_PAGES_PUBLIC_URL", origin.base)
    monkeypatch.setenv("THOR_PAGES_VISIBILITY_TRIES", "5")
    monkeypatch.setenv("THOR_PAGES_VISIBILITY_DELAY_S", "0")
    monkeypatch.delenv("PAGES_DISPOSABLE_RUN", raising=False)
    env = {
        "THOR_ARCHIVE_RELEASE": "ci-archive",
        "PAGES_REPO_DIR": str(worktree),
        "THOR_PAGES_PUBLIC_URL": origin.base,
        "THOR_PAGES_VISIBILITY_TRIES": "5",
        "THOR_PAGES_VISIBILITY_DELAY_S": "0",
        "THOR_FAKE_GH_STATE": str(gh_state),
    }
    namespace = SimpleNamespace(gh=fake, gh_state=gh_state, worktree=worktree,
                                origin=origin, base=origin.base, env=env)
    namespace.store = TransportStore(namespace)
    try:
        yield namespace
    finally:
        origin.close()
