"""Tests for the Remote-Spending gate denial contract (NAS PR #481).

ThorHub has no billing HTTP API, so the old HTTP -> exception mapping
(``thor_cli.nous_billing._raise_for_error``) is gone. The contract survives in the
typed exceptions themselves: a gate denial still carries the wire fields (error
code, actor, recovery, retry) and the ``tui_gateway.billing_view._serialize_billing_error``
envelope the TUI branches on. These assert that contract (CF-4) — not specific copy.
"""

import pytest

from thor_cli.thorhub_billing import (
    BillingAuthError,
    BillingError,
    BillingRateLimited,
    BillingRemoteSpendingRevoked,
    BillingSessionRevoked,
)


def _raise(status, payload, headers=None):
    """Build the typed exception the old HTTP mapping used to raise."""
    error = payload.get("error")
    message = payload.get("message", error)
    if status == 403 and error == "remote_spending_revoked":
        return BillingRemoteSpendingRevoked(
            message, status=status, error=error,
            actor=payload.get("actor"), recovery=payload.get("recovery"),
        )
    if status == 401 and error == "session_revoked":
        return BillingSessionRevoked(
            message, status=status, error=error,
            recovery=payload.get("recovery"),
        )
    if status == 401:
        return BillingAuthError(message, status=status, error=error)
    if status == 503 and error == "temporarily_unavailable":
        retry = int((headers or {}).get("Retry-After", 0) or 0) or None
        return BillingRateLimited(
            message, status=status, error=error, retry_after=retry)
    return BillingError(message, status=status, error=error)


# ── exception mapping (thor_cli.thorhub_billing) ──────────────────────


def test_403_remote_spending_revoked_maps_to_typed_exc_with_actor():
    exc = _raise(403, {"error": "remote_spending_revoked", "recovery": "reconnect", "actor": "admin"})
    assert isinstance(exc, BillingRemoteSpendingRevoked)
    assert exc.actor == "admin"
    assert exc.recovery == "reconnect"


def test_401_session_revoked_is_distinct_from_plain_401():
    revoked = _raise(401, {"error": "session_revoked", "recovery": "login"})
    assert isinstance(revoked, BillingSessionRevoked)
    assert revoked.recovery == "login"

    plain = _raise(401, {"error": "invalid_token"})
    assert isinstance(plain, BillingAuthError)
    assert not isinstance(plain, BillingSessionRevoked)


def test_503_is_rate_limited_not_revoked_and_carries_retry_after():
    exc = _raise(503, {"error": "temporarily_unavailable"}, {"Retry-After": "30"})
    assert isinstance(exc, BillingRateLimited)
    assert not isinstance(exc, BillingRemoteSpendingRevoked)
    assert exc.retry_after == 30


def test_409_idempotency_conflict_passes_through():
    exc = _raise(409, {"error": "idempotency_conflict", "message": "same key, different amount"})
    assert exc.error == "idempotency_conflict"


# ── envelope serialization (tui_gateway.billing_view) ──────────────────────


def test_serialize_carries_actor_recovery_and_retry():
    from tui_gateway.billing_view import _serialize_billing_error

    env = _serialize_billing_error(
        _raise(403, {"error": "remote_spending_revoked", "recovery": "reconnect", "actor": "admin"}))
    assert env["ok"] is False
    assert env["error"] == "remote_spending_revoked"
    assert env["actor"] == "admin"
    assert env["recovery"] == "reconnect"

    limited = _serialize_billing_error(
        _raise(503, {"error": "temporarily_unavailable"}, {"Retry-After": "30"}))
    assert limited["error"] == "temporarily_unavailable"
    assert limited["retry_after"] == 30
