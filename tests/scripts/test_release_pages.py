# tests/scripts/test_release_pages.py — contract tests for the GitHub Pages
# release transport (Fase 2 of the R2 -> GitHub migration). The publisher
# writes into a local thor-agent-releases worktree; no network is touched.

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.releases import pages
from scripts.releases.channels import ChannelConflict
from scripts.releases.pages import PagesChannelStore


@pytest.fixture(autouse=True)
def _clean_pages_env(monkeypatch):
    for name in ("THOR_PAGES_PUBLIC_URL", "PAGES_REPO_DIR", "PAGES_DISPOSABLE_RUN",
                 "R2_DISPOSABLE_RUN", "GITHUB_REPOSITORY_ID"):
        monkeypatch.delenv(name, raising=False)


def test_public_base_url_defaults_to_the_pages_host(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_R2_PUBLIC_URL", raising=False)
    assert pages.public_base_url() == "https://thor726.github.io/thor-agent-releases"
    assert pages.public_base_url("https://example.test/base/") == "https://example.test/base"


def test_put_writes_into_worktree_and_refuses_immutable_overwrite(tmp_path):
    source = tmp_path / "stable.json"
    source.write_bytes(b'{"head":null}\n')
    worktree = tmp_path / "releases-repo"
    pages.put(tag="", key="releases/channels/stable.json", file=str(source),
              key_is_full=True, immutable=True, repo_dir=worktree)
    written = worktree / "releases" / "channels" / "stable.json"
    assert written.read_bytes() == b'{"head":null}\n'

    # Identical bytes are an idempotent retry; different bytes are refused.
    pages.put(tag="", key="releases/channels/stable.json", file=str(source),
              key_is_full=True, immutable=True, repo_dir=worktree)
    source.write_bytes(b'{"head":"other"}\n')
    with pytest.raises(ValueError, match="immutable"):
        pages.put(tag="", key="releases/channels/stable.json", file=str(source),
                  key_is_full=True, immutable=True, repo_dir=worktree)
    assert written.read_bytes() == b'{"head":null}\n'


def test_pages_channel_store_roundtrip_and_cas(tmp_path):
    store = PagesChannelStore(tmp_path)
    assert store.get("releases/channels/stable.json") is None
    store.put("releases/channels/stable.json", b'{"revision":1}\n')
    body, etag = store.get("releases/channels/stable.json")
    assert body == b'{"revision":1}\n'

    store.put("releases/channels/stable.json", b'{"revision":2}\n', etag)
    assert store.get("releases/channels/stable.json")[0] == b'{"revision":2}\n'
    with pytest.raises(ChannelConflict):
        store.put("releases/channels/stable.json", b'{"revision":3}\n', etag)
    assert store.keys("releases/channels/") == ["releases/channels/stable.json"]
