"""ThorHub display surfaces: the paid-tool notice switches wording inside a chat,
and ``thor auth status`` renders ThorHub copy without a key.

Replaces ``test_anon_surfaces.py``: the guest free tier is retired, so the
JWT-dependent surface tests are gone, and with them the copy contract for the
sign-in state machine (``thor_cli.anon_sign_in.SignInState`` is deleted with the
Nous Portal sign-in). What survives is the ThorHub entitlement message and the
``thor auth status`` copy.
"""

from __future__ import annotations

from types import SimpleNamespace

from thor_cli import (
    auth_commands,
    thorhub_account,
)


def test_the_paid_tool_notice_switches_wording_inside_a_chat():
    info = thorhub_account.ThorHubAccountInfo(
        logged_in=True, source="token", fresh=True, account_tier="anonymous"
    )
    assert thorhub_account.format_thorhub_entitlement_message(
        info, in_chat=True
    ) == thorhub_account.FREE_TIER_NEEDS_ACCOUNT_CHAT
    assert thorhub_account.format_thorhub_entitlement_message(
        info, in_chat=False
    ) == thorhub_account.FREE_TIER_NEEDS_ACCOUNT


def test_auth_status_thor_renders_thorhub_copy_without_a_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    monkeypatch.delenv("THORHUB_API_KEY", raising=False)
    auth_commands.auth_status_command(SimpleNamespace(provider="thor"))
    text = capsys.readouterr().out
    assert text.strip() == "thor: logged out"
    assert "nous" not in text.lower()
    assert "portal.thor-agent.local" not in text
