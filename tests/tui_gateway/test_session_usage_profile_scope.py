"""``session.usage`` must not fetch account credits in any profile scope.

The Nous fields are a shape-compat stub since PR #51 (the ThorHub balance lives on
/topup and is read by ``/usage``, not by this RPC), so no profile's key or portal
is touched here — and no cross-profile read can leak through this RPC either.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from tui_gateway import launch_profile_policy as lpp
from tui_gateway import server

LAUNCH_PORTAL = "https://launch-portal.example.invalid"
B_PORTAL = "https://b-portal.example.invalid"


@pytest.fixture
def two_homes(tmp_path, monkeypatch):
    """Launch home (root) + secondary ``profiles/b``, each with its own Portal override, multiplexing on."""
    root = tmp_path / "thor_home"
    b = root / "profiles" / "b"
    b.mkdir(parents=True)
    (root / ".env").write_text(f"THOR_PORTAL_BASE_URL={LAUNCH_PORTAL}\n", encoding="utf-8")
    (b / ".env").write_text(f"THOR_PORTAL_BASE_URL={B_PORTAL}\n", encoding="utf-8")
    for home, token in ((root, "tok-launch"), (b, "tok-b")):
        (home / "config.yaml").write_text("{}\n", encoding="utf-8")
        (home / "auth.json").write_text(
            json.dumps({"version": 1, "providers": {"nous": {"access_token": token}}}), encoding="utf-8")
    monkeypatch.setenv("THOR_HOME", str(root))
    monkeypatch.setenv("THOR_PORTAL_BASE_URL", LAUNCH_PORTAL)  # the launch process loaded its own .env
    monkeypatch.setattr(server, "_thor_home", root)
    monkeypatch.setattr(server, "_served_profile_homes", set())
    monkeypatch.setattr(lpp, "_snapshot", None)
    from agent import secret_scope
    monkeypatch.setattr(secret_scope, "_MULTIPLEX_ACTIVE", False)
    server._cfg_cache = server._cfg_mtime = server._cfg_path = None
    lpp.activate_multi_profile_hosting()
    return root, b


def _session(profile_home):
    return {"agent": None, "session_key": "sess", "profile_home": profile_home,
            "history": [], "history_lock": threading.Lock()}


def test_session_usage_does_not_fetch_account_info_in_any_profile_scope(two_homes, monkeypatch):
    root, b = two_homes
    calls: list = []

    def fake_account_info(**_kwargs):
        calls.append(1)
        raise RuntimeError("no network in tests")

    monkeypatch.setattr("thor_cli.thorhub_account.get_thorhub_account_info", fake_account_info)
    monkeypatch.setattr("thor_cli.thorhub_account.stored_token_account_info", fake_account_info)
    monkeypatch.setattr(server, "_sessions", {"sa": _session(None), "sb": _session(str(b))})

    for sid in ("sa", "sb"):
        res = server._methods["session.usage"]("rid", {"session_id": sid})
        assert "result" in res
        assert res["result"]["thorhub_route"] is False

    assert calls == []


