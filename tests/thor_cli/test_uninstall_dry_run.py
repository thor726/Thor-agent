from pathlib import Path
from types import SimpleNamespace

from thor_cli import uninstall


def test_dry_run_prints_plan_without_mutating(monkeypatch, tmp_path, capsys):
    project_root = tmp_path / "thor-agent"
    thor_home = tmp_path / ".thor"
    project_root.mkdir()
    # A .git dir marks the tree as a removable git checkout — without it the
    # install-kind gate refuses before the dry-run plan prints.
    (project_root / ".git").mkdir()
    thor_home.mkdir()
    (thor_home / "config.yaml").write_text("model: {}\n", encoding="utf-8")

    called = False

    def _fail_if_called(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(uninstall, "get_project_root", lambda: project_root)
    monkeypatch.setattr(uninstall, "get_thor_home", lambda: thor_home)
    monkeypatch.setattr(uninstall, "_is_default_thor_home", lambda home: False)
    monkeypatch.setattr(uninstall, "_discover_named_profiles", list)
    monkeypatch.setattr(uninstall, "_perform_uninstall", _fail_if_called)

    uninstall.run_uninstall(SimpleNamespace(dry_run=True, yes=True, full=True))

    output = capsys.readouterr().out
    assert called is False
    assert "Dry run" in output
    assert str(project_root) in output
    assert str(thor_home) in output
    assert project_root.exists()
    assert thor_home.exists()


def test_dry_run_lists_named_profiles_without_desktop_userdata(monkeypatch, tmp_path, capsys):
    """Full-uninstall dry-run lists named profiles even on a machine with no desktop
    userData dir — the profiles section must not depend on the desktop install."""
    profile = SimpleNamespace(name="work", path=tmp_path / "profiles" / "work")
    monkeypatch.setattr(uninstall, "_is_default_thor_home", lambda home: True)
    monkeypatch.setattr(uninstall, "_discover_named_profiles", lambda: [profile])
    monkeypatch.setattr(
        "thor_cli.gui_uninstall.desktop_userdata_dir", lambda: tmp_path / "absent-userdata"
    )

    uninstall._print_uninstall_dry_run(
        project_root=tmp_path, thor_home=tmp_path / ".thor", full_uninstall=True
    )

    out = capsys.readouterr().out
    assert "Named profiles" in out
    assert "work" in out


def test_build_uninstall_parser_accepts_dry_run():
    import argparse
    from thor_cli.subcommands.uninstall import build_uninstall_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_uninstall_parser(subparsers, cmd_uninstall=lambda args: args)

    args = parser.parse_args(["uninstall", "--dry-run", "--full"])

    assert args.dry_run is True
    assert args.full is True
