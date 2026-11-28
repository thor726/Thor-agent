"""``scripts/ci/catalog_core_imports.py``: the committed index of pinned catalog plugins' core
imports, and the warning when a core change takes one away (never a failure)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import scripts.ci.catalog_core_imports as cci
from thor_cli.plugin_validate_private_imports import CoreImports, ImportBranch, ImportChoice, ImportSite


def _row() -> cci.Row:
    return cci.Row("abc123", "", CoreImports(
        (ImportSite("main.py", 3, "thor_cli.config", "_private_helper"),
         ImportSite("lib/util.py", 1, "thor_cli.plugins", "PluginContext")),
        (ImportChoice((ImportBranch((ImportSite("main.py", 9, "thor_cli.config", "_x"),)),)),),
    ))


def test_write_then_read_index_round_trips_rows_and_shards(tmp_path):
    entries = {"apple": _row(), "banana": cci.Row("def456", "pkg", CoreImports((), ()), "fetch failed: boom")}
    index = tmp_path / "index"

    cci.write_index(entries, index)

    assert (index / "a.json").is_file()
    assert (index / "b.json").is_file()
    assert cci.read_index(index) == entries


def test_index_shards_split_by_first_character(tmp_path):
    entries = {
        "1st": cci.Row("a", "", CoreImports((), ())),
        "_hidden": cci.Row("b", "", CoreImports((), ())),
        "Zebra": cci.Row("c", "", CoreImports((), ())),
    }
    index = tmp_path / "index"

    cci.write_index(entries, index)

    assert {p.name for p in index.glob("*.json")} == {"1.json", "_.json", "z.json"}
    assert cci.read_index(index) == entries


def _repo(tmp_path: Path, base_files: dict[str, str], head_files: dict[str, str | None]):
    """A temp git repo with a base commit and a head commit; returns ``(root, base, head)``."""
    root = tmp_path / "repo"
    root.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
                              cwd=root, check=True, capture_output=True, timeout=60, text=True).stdout.strip()

    git("init", "-q")
    for rel, text in base_files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    base = git("rev-parse", "HEAD")
    for rel, text in head_files.items():
        path = root / rel
        if text is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "head")
    return root, base, git("rev-parse", "HEAD")


def _demo_index() -> dict[str, cci.Row]:
    return {"demo": cci.Row("a" * 40, "", CoreImports(
        (ImportSite("main.py", 3, "thor_cli.config", "_private_helper"),), ()))}


def _demo_entry() -> SimpleNamespace:
    return SimpleNamespace(title="Demo", version="1.0", tier="community", category="tools",
                           maintainer="someone", repo="https://github.com/example/demo-plugin",
                           sha="a" * 40, subdir="")


def test_breaks_reports_a_lost_import_and_report_names_it(tmp_path):
    root, base, head = _repo(tmp_path,
                             {"thor_cli/config.py": "def _private_helper():\n    pass\n"},
                             {"thor_cli/config.py": None})

    found = cci.breaks(_demo_index(), cci.Tree(root, base), cci.Tree(root, head))

    assert len(found) == 1
    assert found[0].plugin == "demo"
    assert found[0].target == "thor_cli.config._private_helper"
    assert found[0].guarded is False
    text = cci.report(found, {"demo": _demo_entry()}, frozenset())
    assert "thor_cli.config._private_helper" in text
    assert "private" in text
    assert "demo" in text


def test_import_never_on_base_is_not_reported(tmp_path):
    root, base, head = _repo(tmp_path, {"other.py": "x = 1\n"}, {"other.py": "x = 2\n"})

    assert cci.breaks(_demo_index(), cci.Tree(root, base), cci.Tree(root, head)) == []


def test_check_warns_about_a_lost_import_but_still_exits_zero(tmp_path, monkeypatch, capsys):
    root, base, head = _repo(tmp_path,
                             {"thor_cli/config.py": "def _private_helper():\n    pass\n"},
                             {"thor_cli/config.py": None})
    catalog_dir = tmp_path / "plugin-catalog"
    catalog_dir.mkdir()
    (catalog_dir / "demo.yaml").write_text(
        "name: demo\nrepo: https://github.com/example/demo-plugin\nsha: " + "a" * 40 + "\n"
        "description: d\nmaintainer: someone\ntier: community\ncategory: tools\n", encoding="utf-8")
    index_dir = tmp_path / "index"
    cci.write_index(_demo_index(), index_dir)
    real_read_index = cci.read_index
    monkeypatch.setattr(cci, "ROOT", root)
    monkeypatch.setattr(cci, "CATALOG", catalog_dir)
    monkeypatch.setattr(cci, "read_index", lambda: real_read_index(index_dir))

    assert cci.check(base, head) == 0
    assert "thor_cli.config._private_helper" in capsys.readouterr().out


def _lost_import_repo(tmp_path, monkeypatch):
    root, base, head = _repo(tmp_path,
                             {"thor_cli/config.py": "def _private_helper():\n    pass\n"},
                             {"thor_cli/config.py": None})
    catalog_dir = tmp_path / "plugin-catalog"
    catalog_dir.mkdir()
    (catalog_dir / "demo.yaml").write_text(
        "name: demo\nrepo: https://github.com/example/demo-plugin\nsha: " + "a" * 40 + "\n"
        "description: d\nmaintainer: someone\ntier: community\ncategory: tools\n", encoding="utf-8")
    index_dir = tmp_path / "index"
    cci.write_index(_demo_index(), index_dir)
    real_read_index = cci.read_index
    monkeypatch.setattr(cci, "ROOT", root)
    monkeypatch.setattr(cci, "CATALOG", catalog_dir)
    monkeypatch.setattr(cci, "read_index", lambda: real_read_index(index_dir))
    return base, head


def test_check_warns_when_ci_sets_github_actions_but_no_runner_temp(tmp_path, monkeypatch, capsys):
    """Regression (rc.4): the Catalog tests job died with KeyError: 'RUNNER_TEMP'.

    run_tests.sh forwards GITHUB_ACTIONS into the hermetic test env but strips
    RUNNER_TEMP, so _publish_warning proceeds in CI and review_status.publish
    crashed the warning path. A warning must never fail the check: with no
    runner temp dir the review-status artifact is simply skipped.
    """
    base, head = _lost_import_repo(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    assert cci.check(base, head) == 0
    assert "thor_cli.config._private_helper" in capsys.readouterr().out


def test_check_writes_review_status_artifact_when_runner_temp_set(tmp_path, monkeypatch, capsys):
    """In CI the warning also lands in the review-status artifact the workflow uploads."""
    base, head = _lost_import_repo(tmp_path, monkeypatch)
    runner_temp = tmp_path / "runner-temp"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_TEMP", str(runner_temp))

    assert cci.check(base, head) == 0
    artifact = runner_temp / "review-status" / "catalog-core-imports" / "review-status.json"
    assert artifact.is_file()
    assert "thor_cli.config._private_helper" in artifact.read_text(encoding="utf-8")
