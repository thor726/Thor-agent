"""Tests for the ThorHub account snapshot (thor_cli.thorhub_account).

ThorHub auth is a static ``sk-thor-...`` key: ``logged_in`` = a key is configured,
``paid_service_access`` = the balance read (``GET /portal/member/me``) succeeded.
There is no OAuth, JWT, pool, subscription, tier, or usage window.
"""

from __future__ import annotations

import pytest

import thor_cli.thorhub_account as account_mod
from thor_cli.thorhub_account import (
    ThorHubAccountInfo,
    ThorHubPaidServiceAccessInfo,
    cached_thorhub_account_info,
    format_thorhub_entitlement_message,
    get_thorhub_account_info,
    reset_thorhub_account_info_cache,
    stored_token_account_info,
    thorhub_billing_url,
    thorhub_policy_notice,
    thorhub_policy_present,
    thorhub_topup_url,
)


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    reset_thorhub_account_info_cache()
    monkeypatch.delenv("THORHUB_API_KEY", raising=False)
    monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
    yield
    reset_thorhub_account_info_cache()


_BALANCE = {
    "token_limit": 1_000_000,
    "tokens_used": 12_304,
    "tokens_remaining": 987_696,
    "key_days_left": 25,
    "is_active": True,
}


def _with_key(monkeypatch, balance=_BALANCE):
    """Configure a ThorHub key whose balance read returns ``balance`` (None = failed read)."""
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "sk-thor-test")
    monkeypatch.setattr(account_mod, "fetch_thorhub_balance", lambda **kw: balance)
    return balance


def test_no_key_is_not_logged_in(monkeypatch):
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "")
    info = get_thorhub_account_info(force_fresh=True)

    assert isinstance(info, ThorHubAccountInfo)
    assert info.logged_in is False
    assert info.source == "none"
    assert info.fresh is False
    assert info.paid_service_access is None
    assert info.is_paid is False
    assert stored_token_account_info() is None


def test_key_with_balance_is_logged_in_and_paid(monkeypatch):
    _with_key(monkeypatch)
    info = get_thorhub_account_info(force_fresh=True)

    assert info.logged_in is True
    assert info.source == "api_key"
    assert info.fresh is True
    assert info.paid_service_access is True
    assert info.is_paid is True
    assert info.is_free_tier is False
    assert info.inference_credential_present is True
    assert info.credential_source == "thorhub_key"
    assert info.inference_base_url == "https://llm.thormarket.site/v1"
    assert info.portal_base_url == "https://llm.thormarket.site"
    assert isinstance(info.paid_service_access_info, ThorHubPaidServiceAccessInfo)
    assert info.paid_service_access_info.total_usable_credits == 987_696.0
    assert info.raw_account == _BALANCE
    assert info.tool_gateway_entitled is False
    assert info.managed_tools_rolled_out is False
    assert info.tool_gateway_entitled_for("fal") is False


def test_key_with_failed_balance_read_reports_balance_unavailable(monkeypatch):
    _with_key(monkeypatch, balance=None)
    info = get_thorhub_account_info(force_fresh=True)

    assert info.logged_in is True
    assert info.source == "api_key"
    assert info.fresh is False
    assert info.paid_service_access is None
    assert info.error == "balance_unavailable"


def test_balance_read_exception_is_an_error_snapshot(monkeypatch):
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "sk-thor-test")
    monkeypatch.setattr(account_mod, "fetch_thorhub_balance", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    info = get_thorhub_account_info(force_fresh=True)

    assert info.logged_in is True
    assert info.source == "error"
    assert "boom" in (info.error or "")


def test_balance_is_cached_for_sixty_seconds(monkeypatch):
    calls = []
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "sk-thor-test")
    monkeypatch.setattr(account_mod, "fetch_thorhub_balance", lambda **kw: calls.append(1) or _BALANCE)

    first = get_thorhub_account_info()
    second = get_thorhub_account_info()
    assert first is second
    assert len(calls) == 1
    assert cached_thorhub_account_info() is first

    # force_fresh bypasses the cache and replaces the snapshot.
    fresh = get_thorhub_account_info(force_fresh=True)
    assert len(calls) == 2
    assert fresh is not first
    assert cached_thorhub_account_info() is fresh

    # The cached snapshot is served to the same key only.
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "sk-thor-other")
    assert cached_thorhub_account_info() is None


def test_cached_snapshot_survives_reset_only_via_reset(monkeypatch):
    _with_key(monkeypatch)
    get_thorhub_account_info()
    assert cached_thorhub_account_info() is not None
    reset_thorhub_account_info_cache()
    assert cached_thorhub_account_info() is None


def test_thorhub_urls():
    assert thorhub_billing_url(None) == "https://llm.thormarket.site/portal"
    assert thorhub_topup_url(None) == "https://llm.thormarket.site/beli/topup"
    info = ThorHubAccountInfo(logged_in=True, source="api_key", fresh=True)
    assert thorhub_billing_url(info) == "https://llm.thormarket.site/portal"
    assert thorhub_topup_url(info) == "https://llm.thormarket.site/beli/topup"


def test_policy_is_always_unknown():
    assert thorhub_policy_present() is None
    assert thorhub_policy_notice(removed=True) == ""
    assert thorhub_policy_notice(removed=False) == ""


def test_entitlement_message_for_unverifiable_account():
    msg = format_thorhub_entitlement_message(None, capability="this feature")
    assert msg is not None and "could not verify" in msg


def test_entitlement_message_for_logged_out_account():
    info = ThorHubAccountInfo(logged_in=False, source="none", fresh=False)
    msg = format_thorhub_entitlement_message(info, capability="this feature")
    assert msg is not None and "thor auth add thor" in msg


def test_entitlement_message_for_unverifiable_balance():
    info = ThorHubAccountInfo(logged_in=True, source="api_key", fresh=False, paid_service_access=None, error="balance_unavailable")
    msg = format_thorhub_entitlement_message(info, capability="this feature")
    assert msg is not None and "could not verify your ThorHub balance" in msg


def test_entitlement_message_for_no_paid_access():
    info = ThorHubAccountInfo(logged_in=True, source="api_key", fresh=True, paid_service_access=False)
    msg = format_thorhub_entitlement_message(info, capability="this feature")
    assert msg is not None and "Top up" in msg


def test_entitlement_message_is_none_when_entitled(monkeypatch):
    _with_key(monkeypatch)
    info = get_thorhub_account_info(force_fresh=True)
    assert format_thorhub_entitlement_message(info, capability="this feature") is None


def test_entitlement_message_for_a_vendor_category():
    info = ThorHubAccountInfo(logged_in=True, source="api_key", fresh=True, paid_service_access=True)
    msg = format_thorhub_entitlement_message(info, capability="image generation", coverage_category="fal")
    assert msg is not None and "ThorHub covers LLM calls only" in msg


def test_anonymous_tier_gets_the_account_message():
    info = ThorHubAccountInfo(logged_in=True, source="api_key", fresh=True, paid_service_access=False, account_tier="anonymous")
    assert format_thorhub_entitlement_message(info, capability="this feature") == (
        "This needs a Thor account. Run `thor auth upgrade`."
    )
    assert format_thorhub_entitlement_message(info, capability="this feature", in_chat=True) == (
        "This needs a Thor account. Use /login to sign in."
    )
