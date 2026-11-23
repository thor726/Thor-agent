"""ThorHub billing (llm.thormarket.site).

ThorHub has no billing API: balances are read-only (``GET /portal/member/me``,
see :mod:`thor_cli.thorhub_account`), and token packages are bought on the
store page (``/beli/topup``). The *write* side of the old Portal client —
charges, auto top-up, subscriptions — raises :class:`BillingError` pointing
at the store, so the terminal billing screens degrade honestly instead of
calling a dead Portal. The typed error hierarchy is kept so callers keep
their ``except`` shapes.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

DEFAULT_PORTAL_BASE_URL = "https://llm.thormarket.site"

DEFAULT_TIMEOUT = 15.0  # tight so a hung portal doesn't freeze the TUI (charge/poll calls are quick)


# --- Typed errors ---


class BillingError(Exception):
    """A billing HTTP call failed; carries server ``error`` code, HTTP ``status``, the ``portalUrl``
    deep-link (present on every gate denial), ``retry_after`` seconds (429/503) and the parsed ``payload``.
    """

    def __init__(
        self, message: str, *, status: Optional[int] = None, error: Optional[str] = None,
        portal_url: Optional[str] = None, retry_after: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None, actor: Optional[str] = None,
        code: Optional[str] = None, recovery: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status, self.error, self.portal_url, self.retry_after = status, error, portal_url, retry_after
        self.payload = payload or {}
        # Remote-Spending contract extras: `actor` (self|admin) on a revoke, `code` (machine code
        # dual-emitted alongside `error`), `recovery` (reconnect|login|enable_account_toggle).
        # Additive — absent on older NAS / unrelated errors.
        self.actor, self.code, self.recovery = actor, code, recovery


class BillingScopeRequired(BillingError):
    """Kept for call-site compatibility; ThorHub has no OAuth scopes, so this never fires."""


class BillingAuthError(BillingError):
    """``401`` — missing/invalid bearer token (not logged in / expired)."""


class BillingRemoteSpendingRevoked(BillingError):
    """Kept for call-site compatibility; ThorHub has no remote-spending revocation."""


class BillingSessionRevoked(BillingAuthError):
    """Kept for call-site compatibility; a ThorHub key is revoked by replacing it, not by a session."""


class BillingTransient(BillingError):
    """Deterministic non-charge outcome: the request definitely did NOT complete at Stripe, so a
    retry after backoff is always safe — never the "maybe charged" ambiguity of a real 5xx/timeout.
    Covers 429 rate limiting, 503 gate-unavailable, Stripe down, and the daily upgrade cap.
    """


class BillingRateLimited(BillingTransient):
    """``429 rate_limited`` or ``503 temporarily_unavailable`` — NOT a payment failure. Carries
    ``retry_after``; never auto-retry-spam (limiter is 5/org/hr + 5/token/hr). A 503 is the gate
    failing closed — back off, do NOT treat as revoked.
    """


class BillingStripeUnavailable(BillingTransient):
    """Kept for call-site compatibility; ThorHub takes no card payments."""


class BillingUpgradeCapExceeded(BillingTransient):
    """Kept for call-site compatibility; ThorHub has no plan upgrades."""


# --- Base-URL + auth resolution ---


def resolve_portal_base_url(state: Optional[dict[str, Any]] = None) -> str:
    """Resolve the ThorHub base URL with precedence: env, stored state, default."""
    env = os.getenv("THORHUB_BASE_URL", "").strip()
    for candidate in (env, state.get("portal_base_url") if state else None):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().rstrip("/")
    return DEFAULT_PORTAL_BASE_URL


def _absolutize_portal_url(portal_url: Optional[str]) -> Optional[str]:
    """Resolve a (possibly relative) server portalUrl against the client's portal base.

    The server emits ``portalUrl`` relative by design; absolute URLs pass through unchanged. urljoin
    needs the trailing slash on the base to join an absolute path like "/billing?..." to the host.
    """
    if not (isinstance(portal_url, str) and portal_url.strip()):
        return portal_url
    return urllib.parse.urljoin(resolve_portal_base_url().rstrip("/") + "/", portal_url)


def invalidate_cached_token() -> None:
    """No-op kept for call-site compatibility (ThorHub keys are static; nothing is cached)."""


def _billing_not_logged_in(exc: Optional[BaseException] = None) -> BillingAuthError:
    """Build the canonical 'not logged in' BillingAuthError (single source)."""
    err = BillingAuthError(
        "Not logged into ThorHub — set THORHUB_API_KEY or run `thor auth add thor`.",
        status=401, error="invalid_token")
    if exc is not None:
        err.__cause__ = exc
    return err


def _topup_error(what: str) -> BillingError:
    """ThorHub has no write-side billing API: point at the store."""
    from thor_cli.thorhub_account import THORHUB_TOPUP_URL

    return BillingError(
        f"ThorHub has no {what}: buy token packages at {THORHUB_TOPUP_URL}.",
        error="thorhub_no_billing_api", portal_url=THORHUB_TOPUP_URL)


def _require_str(value: Any, message: str, error: str) -> str:
    """Return ``value.strip()`` or raise a typed BillingError when it is not a non-blank str."""
    if not (isinstance(value, str) and value.strip()):
        raise BillingError(message, error=error)
    return value.strip()


# --- Reads: ThorHub balance / empty subscription ---


def get_billing_state(*, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub balance as the billing state (read-only; no charges or subscriptions)."""
    from thor_cli.thorhub_account import THORHUB_PORTAL_URL, fetch_thorhub_balance, thorhub_api_key

    if not thorhub_api_key():
        raise _billing_not_logged_in()
    balance = fetch_thorhub_balance(timeout=timeout)
    if balance is None:
        raise BillingError("Could not read your ThorHub balance.", error="balance_unavailable")
    return {"ok": True, **balance, "portalUrl": THORHUB_PORTAL_URL}


def get_subscription_state(*, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub has no subscriptions: always an empty subscription state."""
    from thor_cli.thorhub_account import THORHUB_PORTAL_URL

    return {"ok": True, "subscription": None, "hasSubscription": False, "portalUrl": THORHUB_PORTAL_URL}


# --- Writes: all raise, pointing at the ThorHub store ---


def patch_auto_top_up(
    *, enabled: bool, threshold: float | str, top_up_amount: float | str, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any]:
    """ThorHub has no auto top-up (token packages are bought per order)."""
    raise _topup_error("auto top-up")


def patch_keep_going_on_credits(*, enabled: bool, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub has no usage-window plans, so there is no keep-going setting."""
    raise _topup_error("a keep-going setting")


def post_charge(*, amount_usd: float | str, idempotency_key: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub takes no direct charges: buy a token package on the store page."""
    _require_str(idempotency_key, "Idempotency-Key is required for a charge.", "idempotency_key_required")
    raise _topup_error("direct charges")


def get_charge_status(charge_id: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub has no charges to poll."""
    _require_str(charge_id, "A charge id is required.", "invalid_charge_id")
    raise _topup_error("charge polling")


def post_subscription_preview(*, subscription_type_id: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub has no subscriptions to preview."""
    raise _topup_error("subscription previews")


def put_subscription_pending_change(
    *, subscription_type_id: str | None = None, cancel: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any]:
    """ThorHub has no subscriptions to change."""
    raise _topup_error("subscription changes")


def delete_subscription_pending_change(*, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """ThorHub has no subscriptions to change."""
    raise _topup_error("subscription changes")


def post_subscription_upgrade(
    *, subscription_type_id: str, idempotency_key: str, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any]:
    """ThorHub has no subscriptions to upgrade."""
    _require_str(idempotency_key, "Idempotency-Key is required for an upgrade.", "idempotency_key_required")
    raise _topup_error("subscription upgrades")
