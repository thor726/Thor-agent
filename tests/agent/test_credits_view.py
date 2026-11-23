"""Tests for the /topup balance view — ThorHub edition (agent/thorhub_usage.py).

``/topup`` is the focused money surface (balance in, top-up out). These tests
exercise the surface-agnostic ``build_credits_view()`` core: a ThorHub token
balance when THORHUB_API_KEY is set, fail-open (``logged_in=False``) when there
is no key or the fetch fails. The old Nous Portal dollar-credits view is gone
with ``agent.account_usage_nous``.
"""

from __future__ import annotations

import pytest

from agent.thorhub_usage import CreditsView, build_credits_view
from thor_cli.thorhub_account import THORHUB_TOPUP_URL


def _balance(**over):
    data = {
        "user_name": "Tes",
        "token_limit": 1_000_000,
        "tokens_used": 36_908,
        "tokens_remaining": 963_092,
        "key_days_left": 24,
    }
    data.update(over)
    return data


@pytest.fixture
def _stub_balance(monkeypatch):
    """Stub the ThorHub fetch so build_credits_view runs offline."""
    def _install(data):
        monkeypatch.setattr("thor_cli.thorhub_account.fetch_thorhub_balance", lambda: data)
    return _install


def test_view_logged_out_when_no_key(_stub_balance):
    _stub_balance(None)
    view = build_credits_view()
    assert view == CreditsView(logged_in=False)
    assert view.topup_url is None


def test_view_built_with_thorhub_balance_and_identity(_stub_balance):
    _stub_balance(_balance())
    view = build_credits_view()
    assert view.logged_in is True
    assert view.topup_url == THORHUB_TOPUP_URL
    assert view.identity_line and "ThorHub" in view.identity_line and "Tes" in view.identity_line
    assert view.balance_lines, "the balance block must render the ThorHub numbers"
    assert view.depleted is False


def test_view_depleted_when_remaining_zero(_stub_balance):
    _stub_balance(_balance(tokens_remaining=0, tokens_used=1_000_000))
    assert build_credits_view().depleted is True


def test_view_fail_open_when_fetch_raises(monkeypatch):
    monkeypatch.setattr(
        "thor_cli.thorhub_account.fetch_thorhub_balance",
        lambda: (_ for _ in ()).throw(RuntimeError("kaboom")),
    )
    assert build_credits_view().logged_in is False


def test_view_importable_from_account_usage_facade():
    """Published plugin API: catalog plugins import build_credits_view from agent.account_usage."""
    from agent.account_usage import build_credits_view as facade_view
    assert facade_view is build_credits_view
