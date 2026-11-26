"""Every verified Pages upload lands in the GitHub step summary, with its public URL."""
import pytest

from scripts.releases import pages, upload_summary


BASE = "https://thor726.github.io/thor-agent-releases"
KEY = "releases/commit/" + "a" * 40 + "/ThorBundled-1.2.3-win-x64.msix"


@pytest.fixture(autouse=True)
def clear_notes():
    upload_summary._KEYS.clear()
    upload_summary._REGISTERED = False
    yield
    upload_summary._KEYS.clear()


def test_render_uses_the_public_asset_host(monkeypatch):
    monkeypatch.delenv("THOR_PAGES_PUBLIC_URL", raising=False)
    monkeypatch.delenv("PAGES_DISPOSABLE_RUN", raising=False)
    text = upload_summary.render([KEY])
    assert f"[download]({BASE}/{KEY})" in text
    assert text.startswith("\n### R2 uploads\n")
    assert upload_summary.render([]) == ""


def test_render_names_a_key_whose_url_cannot_be_built(monkeypatch):
    monkeypatch.setattr(pages, "public_url_for",
                        lambda base, key: (_ for _ in ()).throw(ValueError("bad key")))
    text = upload_summary.render(["../escape"])
    assert "`../escape`" in text
    assert "| — |" in text


def test_note_dedupes_and_flush_appends_once(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    summary.write_text("existing\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.delenv("THOR_PAGES_PUBLIC_URL", raising=False)
    monkeypatch.delenv("PAGES_DISPOSABLE_RUN", raising=False)
    upload_summary.note(KEY)
    upload_summary.note(KEY)
    upload_summary.flush()
    upload_summary.flush()
    text = summary.read_text(encoding="utf-8")
    assert text.count("### R2 uploads") == 1
    assert text.startswith("existing\n")
    assert f"{BASE}/{KEY}" in text


def test_flush_without_a_summary_keeps_the_notes(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    upload_summary.note(KEY)
    upload_summary.flush()
    assert upload_summary._KEYS == [KEY]


def test_pages_put_records_only_after_the_write_lands(tmp_path, monkeypatch):
    recorded = []
    monkeypatch.setattr(upload_summary, "note", recorded.append)
    worktree = tmp_path / "pages-host"
    source = tmp_path / "payload.bin"
    source.write_bytes(b"payload-bytes")
    pages.put(tag="", key=KEY, file=str(source), key_is_full=True, repo_dir=worktree)
    assert recorded == [KEY]
    # An immutable conflict refuses the write and records nothing.
    source.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="immutable"):
        pages.put(tag="", key=KEY, file=str(source), key_is_full=True, immutable=True, repo_dir=worktree)
    assert recorded == [KEY]
