"""Tests for the ThorHub billing module (thor_cli.thorhub_billing).

ThorHub has no billing API: the balance is read-only (via thorhub_account),
token packages are bought on the store page, and every write-side call raises
:class:`BillingError` pointing at the top-up URL. The typed error hierarchy is
kept so callers keep their ``except`` shapes.
"""

from __future__ import annotations

import pytest

from thor_cli import thorhub_billing as nb
import thor_cli.thorhub_account as account_mod


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("THORHUB_API_KEY", raising=False)
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "")
    yield


_BALANCE = {
    "token_limit": 1_000_000,
    "tokens_used": 12_304,
    "tokens_remaining": 987_696,
    "key_days_left": 25,
    "is_active": True,
}


def _with_key(monkeypatch, balance=_BALANCE):
    monkeypatch.setattr(account_mod, "thorhub_api_key", lambda: "sk-thor-test")
    monkeypatch.setattr(account_mod, "fetch_thorhub_balance", lambda **kw: balance)


def test_get_billing_state_without_a_key_is_auth_error():
    with pytest.raises(nb.BillingAuthError) as ei:
        nb.get_billing_state()
    assert ei.value.status == 401
    assert ei.value.error == "invalid_token"


def test_get_billing_state_returns_the_thorhub_balance(monkeypatch):
    _with_key(monkeypatch)
    state = nb.get_billing_state()

    assert state["ok"] is True
    assert state["tokens_remaining"] == 987_696
    assert state["token_limit"] == 1_000_000
    assert state["portalUrl"] == "https://llm.thormarket.site/portal"


def test_get_billing_state_with_failed_balance_read(monkeypatch):
    _with_key(monkeypatch, balance=None)
    with pytest.raises(nb.BillingError) as ei:
        nb.get_billing_state()
    assert ei.value.error == "balance_unavailable"


def test_get_subscription_state_is_always_empty():
    assert nb.get_subscription_state() == {
        "ok": True,
        "subscription": None,
        "hasSubscription": False,
        "portalUrl": "https://llm.thormarket.site/portal",
    }


@pytest.mark.parametrize(
    "call",
    [
        lambda: nb.post_charge(amount_usd=10, idempotency_key="k-1"),
        lambda: nb.get_charge_status("ch_1"),
        lambda: nb.post_subscription_preview(subscription_type_id="tier-2"),
        lambda: nb.put_subscription_pending_change(subscription_type_id="tier-1"),
        lambda: nb.delete_subscription_pending_change(),
        lambda: nb.post_subscription_upgrade(subscription_type_id="tier-2", idempotency_key="k-2"),
        lambda: nb.patch_auto_top_up(enabled=True, threshold=5, top_up_amount=10),
        lambda: nb.patch_keep_going_on_credits(enabled=True),
    ],
)
def test_write_calls_raise_pointing_at_the_store(call):
    with pytest.raises(nb.BillingError) as ei:
        call()
    assert ei.value.error == "thorhub_no_billing_api"
    assert "https://llm.thormarket.site/beli/topup" in str(ei.value)
    assert ei.value.portal_url == "https://llm.thormarket.site/beli/topup"


def test_post_charge_requires_an_idempotency_key():
    with pytest.raises(nb.BillingError) as ei:
        nb.post_charge(amount_usd=10, idempotency_key="  ")
    assert ei.value.error == "idempotency_key_required"


def test_post_subscription_upgrade_requires_an_idempotency_key():
    with pytest.raises(nb.BillingError) as ei:
        nb.post_subscription_upgrade(subscription_type_id="tier-2", idempotency_key="")
    assert ei.value.error == "idempotency_key_required"


def test_get_charge_status_requires_a_charge_id():
    with pytest.raises(nb.BillingError) as ei:
        nb.get_charge_status("")
    assert ei.value.error == "invalid_charge_id"


def test_resolve_portal_base_url_defaults_to_thorhub(monkeypatch):
    monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
    assert nb.resolve_portal_base_url() == "https://llm.thormarket.site"
    assert nb.resolve_portal_base_url({"portal_base_url": "https://example.test/"}) == "https://example.test"


def test_resolve_portal_base_url_env_override(monkeypatch):
    monkeypatch.setenv("THORHUB_BASE_URL", "https://staging.example.test/")
    assert nb.resolve_portal_base_url() == "https://staging.example.test"


def test_absolutize_portal_url_joins_relative_urls():
    assert nb._absolutize_portal_url("/beli/topup") == "https://llm.thormarket.site/beli/topup"
    assert nb._absolutize_portal_url("https://other.example/x") == "https://other.example/x"
    assert nb._absolutize_portal_url(None) is None


def test_invalidate_cached_token_is_a_noop():
    assert nb.invalidate_cached_token() is None


def test_billing_error_carries_its_fields():
    err = nb.BillingError(
        "boom", status=429, error="rate_limited", portal_url="https://x",
        retry_after=15, payload={"a": 1}, actor="self", code="c", recovery="r",
    )
    assert err.status == 429
    assert err.error == "rate_limited"
    assert err.portal_url == "https://x"
    assert err.retry_after == 15
    assert err.payload == {"a": 1}
    assert err.actor == "self"
    assert err.code == "c"
    assert err.recovery == "r"
    assert isinstance(nb.BillingScopeRequired("x"), nb.BillingError)
    assert isinstance(nb.BillingSessionRevoked("x"), nb.BillingAuthError)
    assert isinstance(nb.BillingRateLimited("x"), nb.BillingTransient)
