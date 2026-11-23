"""slash.exec /usage: there is no Nous block anymore — /usage shows only the
provider's account limits, whatever the last reply's credits state says.
(The ThorHub balance lives on /topup.)"""

from __future__ import annotations

import contextlib
import threading
from types import SimpleNamespace

from tui_gateway import server


def _session(state):
    agent = SimpleNamespace(model="m", provider="openai-codex", _credits_state=state)
    return {"agent": agent, "history": [], "history_lock": threading.Lock()}


def _render(monkeypatch, state):
    monkeypatch.setattr("agent.account_usage.fetch_account_usage", lambda *a, **kw: None)
    monkeypatch.setattr(server, "_session_profile_runtime_scope", lambda session, **kw: contextlib.nullcontext())
    monkeypatch.setattr(server, "_config_model_target", lambda: ("", ""))
    monkeypatch.setattr(server, "_session_usage_snapshot", lambda session: {"model": "m"})
    monkeypatch.setattr(server, "_metadata_mirror", lambda session: {})
    return server._format_live_usage_output("sid", _session(state), "")


def test_no_nous_block_without_credits_state(monkeypatch):
    assert "Nous" not in _render(monkeypatch, None)


def test_no_nous_block_with_non_window_credits_state(monkeypatch):
    assert "Nous" not in _render(monkeypatch, SimpleNamespace(is_usage_window=False))


def test_no_nous_block_with_window_credits_state(monkeypatch):
    assert "Nous" not in _render(monkeypatch, SimpleNamespace(is_usage_window=True))
