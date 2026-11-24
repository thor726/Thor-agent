"""``free_tier.status`` / ``free_tier.provision`` / ``free_tier.ack_notice`` and the free-tier
branch of ``billing.state`` — retired with the guest free tier.

The handlers still exist and answer honestly: there is no guest, the trial cannot be claimed,
and no free-tier account exists. Nothing touches the network. The fake portal fixture stays only
to prove that: a provision or status poll must not call it.
"""

from __future__ import annotations

import pytest

import tui_gateway.server as srv
from thor_cli import anon_auth, free_tier_offer
from thor_cli.auth import _auth_store_lock, _load_auth_store, _save_auth_store
from tests.thor_cli.anon_portal import as_local_desktop_backend, install_portal


def _call(method: str, params: dict | None = None) -> dict:
    return srv._methods[method](1, params or {})["result"]


@pytest.fixture
def nas(tmp_path, monkeypatch):
    """The fake account service, read on the desktop's local backend of a first install."""
    fake = install_portal(monkeypatch, tmp_path)
    as_local_desktop_backend(monkeypatch)
    return fake


def _retired_status() -> dict:
    return {"has_guest": False, "enabled": False, "available": False, "notice_pending": False,
            "model": "nous/welcome", "label": anon_auth.FREE_TIER_LABEL}


def test_status_is_a_pure_read_without_an_identity(nas):
    status = _call("free_tier.status")
    assert status == _retired_status()
    assert nas.calls == []


def test_status_reports_no_guest_for_a_legacy_guest_state(nas):
    """A guest state left on disk by an older Thor no longer reads as a free tier."""
    with _auth_store_lock():
        store = _load_auth_store()
        store.setdefault("providers", {})["nous"] = {
            "auth_method": "anonymous", "access_token": "legacy-guest-jwt",
            "account_tier": "anonymous"}
        _save_auth_store(store)
    assert _call("free_tier.status") == _retired_status()
    assert nas.calls == []


def test_provision_does_nothing_when_the_trial_is_retired(nas):
    assert _call("free_tier.provision") == {"has_guest": False, "enabled": False}
    assert nas.calls == []


def test_ack_notice_reports_nothing_to_ack(nas):
    assert _call("free_tier.ack_notice") == {"acked": False}


def test_status_never_carries_a_challenge(nas):
    assert "challenge" not in _call("free_tier.status")
    assert _call("free_tier.challenge_result",
                 {"url": "https://portal.example.test/challenge?code=t", "outcome": "done"}) == {"accepted": False}


def test_billing_state_has_no_free_tier_account(nas):
    # No key, no guest: the empty billing state, not the free-tier local answer.
    res = _call("billing.state")
    assert res["ok"] is True and res["logged_in"] is False
    assert res["free_tier_account"] is False
    assert res["error"] is None
    assert nas.calls == []


def test_sign_in_offer_is_never_due_without_a_free_tier(nas, monkeypatch):
    now = [10_000.0]
    monkeypatch.setattr(free_tier_offer, "_clock", lambda: now[0])
    assert "nudge_due_in" not in _call("free_tier.status")
    assert _call("free_tier.claim_nudge") == {"claimed": False}

    free_tier_offer.record_task_done()
    now[0] += free_tier_offer.OFFER_DELAY_S
    assert "nudge_due_in" not in _call("free_tier.status")
    assert _call("free_tier.claim_nudge") == {"claimed": False}


def test_sign_in_offer_is_moot_once_signed_in(nas, monkeypatch):
    """A ThorHub key is a signed-in account: no sign-in offer is ever due for it either."""
    monkeypatch.setattr(free_tier_offer, "_clock", lambda: 10_000.0)
    free_tier_offer.record_task_done()
    with _auth_store_lock():
        store = _load_auth_store()
        store["providers"]["thor"] = {"api_key": "sk-thor-test"}
        _save_auth_store(store)
    assert "nudge_due_in" not in _call("free_tier.status")
    assert _call("free_tier.claim_nudge") == {"claimed": False}
