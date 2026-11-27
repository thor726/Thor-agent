"""``--detach`` flags and the refused-run record for ``thor gateway migrate --backends`` (Fase 2).

Behaviour contracts only: the background run's own flags, and the
``detached-refused.json`` a refused run leaves for ``--status``.
"""

from __future__ import annotations

from types import SimpleNamespace

from thor_cli import gateway_migrate_backends_detach as detach


def _args(**overrides):
    args = {"address": None, "keep_webapp_address": False, "force_interrupt": False,
            "expect": None, "json": False}
    args.update(overrides)
    return SimpleNamespace(**args)


def test_detached_flags_for_apply(tmp_path):
    flags = detach.detached_flags(_args(), "apply", tmp_path / "home")
    assert flags == ["gateway", "migrate", "--backends", "--apply", "--yes", "--detached-run"]


def test_detached_flags_for_restore(tmp_path):
    flags = detach.detached_flags(_args(), "restore", tmp_path / "home")
    assert flags == ["gateway", "migrate", "--backends", "--restore", "--yes", "--detached-run"]


def test_detached_flags_carry_the_confirmed_options(tmp_path):
    flags = detach.detached_flags(
        _args(address="127.0.0.1:9119", keep_webapp_address=True,
              force_interrupt=True, expect="tok123"),
        "apply", tmp_path / "home")
    assert flags == ["gateway", "migrate", "--backends", "--apply", "--yes", "--detached-run",
                     "--address", "127.0.0.1:9119", "--keep-webapp-address", "--force-interrupt",
                     "--expect", "tok123"]


def test_exit_unconfirmed_is_7():
    assert detach.EXIT_UNCONFIRMED == 7


def _host(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return SimpleNamespace(home=home, now=lambda: 1700000000.0)


def test_refusal_roundtrip_and_status(tmp_path):
    host = _host(tmp_path)
    detach.record_refusal(host, mode="apply", reason="blocked by preflight",
                          exit_code=3, old_address="127.0.0.1:9119")
    refusal = detach.read_refusal(host.home)
    assert refusal is not None and refusal["reason"] == "blocked by preflight"
    assert refusal["exit_code"] == 3 and refusal["at"] == 1700000000.0
    status = detach.refusal_status(refusal, None)
    assert status is not None
    assert status["state"] == "failed" and status["refused"] is True
    assert "did not start" in status["message"] and "nothing changed" in status["message"]
    detach.clear_refusal(host.home)
    assert detach.read_refusal(host.home) is None


def test_refusal_loses_to_a_live_or_newer_manifest(tmp_path):
    host = _host(tmp_path)
    detach.record_refusal(host, mode="restore", reason="nothing to restore", exit_code=3)
    refusal = detach.read_refusal(host.home)
    assert detach.refusal_status(refusal, {"state": "running"}) is None
    assert detach.refusal_status(refusal, {"state": "done", "finished_at": 1700000001.0}) is None
    assert detach.refusal_status(refusal, {"state": "done", "finished_at": 1699999999.0}) is not None
