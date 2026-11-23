"""ThorHub display surfaces: no sign-in copy leaks internal vocabulary or a
terminal verb, and the paid-tool notice switches wording inside a chat.

Replaces ``test_anon_surfaces.py``: the guest free tier is retired, so the
JWT-dependent surface tests are gone. What survives is the copy contract for
the sign-in state machine (now a retired stub: it yields Failed, or
AlreadySignedIn when a ThorHub key is configured) and the ThorHub entitlement
message.
"""

from __future__ import annotations

import dataclasses
import re
from types import SimpleNamespace

from thor_cli import (
    anon_auth,
    auth_commands,
    guest_handoff,
    thorhub_account,
)

# Words that must never appear on a user-facing sign-in surface.
_FORBIDDEN = re.compile(r"guest|anonymous|user id|org id|nas_user|nas_organisation", re.IGNORECASE)


def test_no_chat_copy_of_any_sign_in_state_leaks_a_terminal_verb_or_a_forbidden_word():
    placeholders = {
        "link": "https://example.test/sign-in",
        "code": "code-1",
        "expires_in": 900,
        "interval": 1,
        "email": "person@example.test",
        "model": "model-1",
        "model_changed": True,
        "reason": "unknown",
        "detail": "private detail",
        "retry_after": 0.0,
        # The retired handoff carries no result lines and no live status.
        "handoff": tuple(guest_handoff.result_lines({})),
        "handoff_status": guest_handoff.wire_status(None),
    }
    forbidden = re.compile(r"claim|nous portal|anonymous|guest", re.IGNORECASE)
    terminal_or_url = re.compile(r"thor |https?://", re.IGNORECASE)

    for state_type in anon_auth.SignInState.__subclasses__():
        kwargs = {field.name: placeholders[field.name] for field in dataclasses.fields(state_type)}
        copy = state_type(**kwargs).copy
        assert _FORBIDDEN.search(copy) is None, state_type.__name__
        assert forbidden.search(copy) is None, state_type.__name__
        assert terminal_or_url.search(copy) is None, state_type.__name__


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
