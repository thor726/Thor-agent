"""A backend migration's retired unit stays stopped (Fase 4, adaptasi A9).

``_restart_managed_dashboard_service`` must not restart an inactive
``thor-dashboard.service`` whose migration manifest says the backend was moved
to the gateway — a `static` unit is never `disabled`, so the enabled check
alone cannot tell. An active unit is still restarted, and without a manifest
the old behaviour (restart the inactive unit) is unchanged.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from thor_cli import main_dashboard

UNIT = "thor-dashboard.service"


def _fake_systemctl(monkeypatch, calls, *, active="inactive", enabled="static", restart_code=0):
    """Answer systemctl probes for a user-scope unit; record every command."""

    def run_probe(cmd, *, timeout):
        calls.append(list(cmd))
        if "list-unit-files" in cmd:
            listed = "--user" in cmd
            return SimpleNamespace(
                returncode=0 if listed else 1,
                stdout=f"{UNIT} {enabled} {enabled}\n" if listed else "", stderr="")
        if "is-active" in cmd:
            return SimpleNamespace(returncode=0, stdout=f"{active}\n", stderr="")
        if "is-enabled" in cmd:
            return SimpleNamespace(returncode=0, stdout=f"{enabled}\n", stderr="")
        if "restart" in cmd:
            return SimpleNamespace(returncode=restart_code, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(main_dashboard, "_run_probe", run_probe)


def _write_manifest(monkeypatch, home, state):
    (home / "backend_migration.json").write_text(json.dumps({"state": state}), encoding="utf-8")


@pytest.mark.platforms("posix")
def test_a_retired_inactive_static_unit_stays_stopped(monkeypatch, tmp_path, capsys):
    from thor_constants import get_thor_home
    home = get_thor_home()
    _write_manifest(monkeypatch, home, "done")
    calls: list = []
    _fake_systemctl(monkeypatch, calls)
    assert main_dashboard._restart_managed_dashboard_service("update") is True
    out = capsys.readouterr().out
    assert f"{UNIT} stays stopped: this profile's backend was moved to the gateway" in out
    assert "(backend_migration.json)." in out
    assert not any("restart" in cmd for cmd in calls), calls


@pytest.mark.platforms("posix")
def test_without_a_manifest_the_inactive_unit_is_restarted(monkeypatch, capsys):
    calls: list = []
    _fake_systemctl(monkeypatch, calls)
    assert main_dashboard._restart_managed_dashboard_service("update") is True
    out = capsys.readouterr().out
    assert f"✓ restarted {UNIT}" in out
    assert ["systemctl", "--user", "restart", UNIT] in calls


@pytest.mark.platforms("posix")
def test_an_active_unit_is_restarted_even_after_a_migration(monkeypatch, tmp_path, capsys):
    from thor_constants import get_thor_home
    home = get_thor_home()
    _write_manifest(monkeypatch, home, "done")
    calls: list = []
    _fake_systemctl(monkeypatch, calls, active="active")
    assert main_dashboard._restart_managed_dashboard_service("update") is True
    out = capsys.readouterr().out
    assert "stays stopped" not in out
    assert ["systemctl", "--user", "restart", UNIT] in calls


@pytest.mark.platforms("posix")
def test_a_restored_manifest_does_not_block_the_restart(monkeypatch, tmp_path, capsys):
    from thor_constants import get_thor_home
    home = get_thor_home()
    _write_manifest(monkeypatch, home, "restored")
    calls: list = []
    _fake_systemctl(monkeypatch, calls)
    assert main_dashboard._restart_managed_dashboard_service("update") is True
    out = capsys.readouterr().out
    assert "stays stopped" not in out
    assert ["systemctl", "--user", "restart", UNIT] in calls
