"""Klien saldo + info akun ThorHub (llm.thormarket.site).

Dipakai ``/topup`` (agent, via ``agent.thorhub_usage``) dan CLI ``_show_billing``.
Saldo dibaca lewat ``GET /portal/member/me`` dengan header
``Authorization: Bearer <key ThorHub>``. Key dibaca dari env ``THORHUB_API_KEY``
(alias ``thorhub`` di config Thor), lalu provider ``thor`` di auth store
(``nous`` lama ikut dibaca sebagai jembatan migrasi). Fungsi di sini tidak
pernah melempar: gagal (tidak ada key, jaringan, key salah) -> ``None``.

Info akun (``ThorHubAccountInfo``) adalah snapshot yang sama dalam bentuk
yang dipakai pemilih model / billing: ``logged_in`` = key terkonfigurasi,
saldo dari ``/portal/member/me`` di-cache 60 detik. ThorHub tidak punya
OAuth, JWT, subscription, tier, atau usage window — semua itu None/False.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone, UTC
from typing import Any, Literal, Optional


THORHUB_BASE_URL = "https://llm.thormarket.site"
THORHUB_TOPUP_URL = f"{THORHUB_BASE_URL}/beli/topup"
THORHUB_PORTAL_URL = f"{THORHUB_BASE_URL}/portal"
THORHUB_PACKAGES_URL = f"{THORHUB_BASE_URL}/beli"
THORHUB_API_BASE_URL = f"{THORHUB_BASE_URL}/v1"


def thorhub_api_key() -> str:
    """Key ThorHub dari env (alias thorhub), lalu provider ``thor`` di auth store.

    Provider ``nous`` lama ikut dibaca sebagai jembatan migrasi (alias provider
    ``thor`` masih menerima ``nous*``) agar auth store lama tetap jalan.
    String kosong bila tidak ada. Tidak pernah melempar.
    """
    if key := (os.environ.get("THORHUB_API_KEY") or "").strip():
        return key
    try:
        from thor_cli.auth import get_provider_auth_state

        for provider in ("thor", "nous"):
            state = get_provider_auth_state(provider) or {}
            for field in ("api_key", "key"):
                value = state.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except Exception:
        pass
    # Credential pool: ``thor auth add thor`` writes its key here (the generic
    # API-key path), mirroring ``thor_cli.auth._resolve_api_key_provider_secret``.
    try:
        from agent.credential_pool import load_pool
        pool = load_pool("thor")
        if pool and pool.has_credentials():
            entry = pool.peek()
            candidates = [entry] if entry is not None else []
            for extra in pool.entries():
                if extra is not None and all(extra is not c for c in candidates):
                    candidates.append(extra)
            for entry in candidates:
                value = getattr(entry, "access_token", "") or getattr(entry, "runtime_api_key", "")
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except Exception:
        pass
    return ""


def thorhub_base_url_env_override() -> Optional[str]:
    """Profile-scoped THORHUB_BASE_URL override (legacy NOUS_INFERENCE_BASE_URL
    accepted), bare origin or None.

    Read through thor_cli.config.get_env_value so a multiplexed profile uses its own
    override instead of the default profile process-wide value (#65941).
    """
    from thor_cli.config import get_env_value

    for name in ("THORHUB_BASE_URL", "NOUS_INFERENCE_BASE_URL"):
        raw = (get_env_value(name) or "").strip()
        if raw:
            return raw.rstrip("/").removesuffix("/v1")
    return None


def resolve_thorhub_base_url() -> str:
    """Base URL ThorHub (portal/member): env override wins, else production."""
    return thorhub_base_url_env_override() or THORHUB_BASE_URL


def _fmt_id(n: object) -> str:
    """1234567 -> "1.234.567" (format Indonesia); gagal -> str apa adanya."""
    try:
        return f"{int(n):,}".replace(",", ".")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(n)


def fetch_thorhub_balance(*, timeout: float = 10.0) -> dict | None:
    """Saldo key ThorHub (dict dari ``/portal/member/me``) atau None bila gagal."""
    key = thorhub_api_key()
    if not key:
        return None
    req = urllib.request.Request(
        f"{resolve_thorhub_base_url()}/portal/member/me",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except Exception:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else None


def format_thorhub_balance_lines(data: dict) -> tuple[str, ...]:
    """Baris saldo (token, bukan USD) untuk ditampilkan di /topup."""
    limit = data.get("token_limit")
    used = data.get("tokens_used")
    remaining = data.get("tokens_remaining")
    if remaining is None and limit is not None and used is not None:
        try:
            remaining = max(0, int(limit) - int(used))
        except (TypeError, ValueError):
            remaining = None
    lines = ["Saldo ThorHub (token AI):"]
    if limit is not None and used is not None:
        lines.append(f"  Terpakai: {_fmt_id(used)} / {_fmt_id(limit)} token")
    if remaining is not None:
        lines.append(f"  Sisa kuota: {_fmt_id(remaining)} token")
    days = data.get("key_days_left")
    if days is not None:
        lines.append(f"  Masa aktif key: {days} hari lagi")
    if data.get("is_active") is False:
        lines.append("  Key sedang nonaktif — hubungi admin ThorHub.")
    lines.append(f"  Top-up: {THORHUB_TOPUP_URL}")
    lines.append(f"  Portal member: {THORHUB_PORTAL_URL}")
    return tuple(lines)


ThorHubAccountInfoSource = Literal["api_key", "none", "error"]

# Free tool-pool coverage categories, byte-aligned with the Portal's TOOL_COVERAGE_CATEGORIES
# (minted into `tool_access.coverage` on the JWT and /api/oauth/account). `fal-video` is
# intentionally excluded from the pool.
TOOL_COVERAGE_CATEGORIES = ("firecrawl", "fal", "fal-video", "openai-audio", "browser-use", "modal")

_ACCOUNT_INFO_CACHE_TTL = 60
_account_info_cache: tuple[str, float, ThorHubAccountInfo] | None = None
_ACCOUNT_INFO_CACHE_LOCK = threading.Lock()
# Who ``_account_info_cache`` belongs to (portal + JWT user/org), for ``cached_thorhub_account_info``:
# that read must survive a token refresh, which changes the cache key above.
_account_info_identity: Optional[str] = None


@dataclass(frozen=True)
class ThorHubSubscriptionInfo:
    plan: Optional[str] = None
    tier: Optional[int] = None
    monthly_charge: Optional[float] = None
    monthly_credits: Optional[float] = None
    current_period_end: Optional[str] = None
    credits_remaining: Optional[float] = None
    rollover_credits: Optional[float] = None


@dataclass(frozen=True)
class ThorHubPaidServiceAccessInfo:
    allowed: Optional[bool] = None
    paid_access: Optional[bool] = None
    reason: Optional[str] = None
    organisation_id: Optional[str] = None
    effective_at_ms: Optional[int] = None
    has_active_subscription: Optional[bool] = None
    active_subscription_is_paid: Optional[bool] = None
    subscription_tier: Optional[int] = None
    subscription_monthly_charge: Optional[float] = None
    subscription_credits_remaining: Optional[float] = None
    purchased_credits_remaining: Optional[float] = None
    total_usable_credits: Optional[float] = None
    member_spend_cap_exceeded: Optional[bool] = None
    member_spend_cap_usd: Optional[float] = None
    member_spend_usd: Optional[float] = None
    member_spend_cap_remaining_usd: Optional[float] = None


@dataclass(frozen=True)
class ThorHubUsageWindowInfo:
    """Portal ``usage_window`` block: a usage-window plan's allowances (``gauges``, the server's list in
    display order; see agent/usage_gauges.py), auto top-up, a paused reason while the plan's renewal is
    unpaid, and the plan's picks. Absent from the account body for every other account."""

    # The server's allowance list (agent.usage_gauges.WindowGauge). None when the portal sends none.
    gauges: Optional[tuple[Any, ...]] = None
    # The plan's recommended picks, in order: pickers list them first, and they are the
    # models a limit line suggests. Every model is usable on the plan.
    featured_model_ids: Optional[tuple[str, ...]] = None
    auto_top_up_enabled: Optional[bool] = None
    paused_reason: Optional[str] = None
    # The account's "Keep going on credits" setting; None from a portal
    # that predates it (top-up is spent then, as before).
    keep_going_on_credits: Optional[bool] = None


@dataclass(frozen=True)
class ThorHubToolAccessInfo:
    """Free tool-pool entitlement (Portal ``tool_access``), decoupled from paid/billing access.

    ``enabled``: a positive pool balance is live and not gated off; ``coverage``: tool category ->
    whether the pool funds it (FAL video is excluded).
    """

    enabled: bool = False
    coverage: dict[str, bool] = field(default_factory=dict)


_ANON_ACCOUNT_TIER = "anonymous"
# Every billing / top-up / entitlement surface says exactly this for the free tier (R-USR-1).
FREE_TIER_NEEDS_ACCOUNT = "This needs a Thor account. Run `thor auth upgrade`."
FREE_TIER_NEEDS_ACCOUNT_CHAT = "This needs a Thor account. Use /login to sign in."


def _is_anonymous_tier(account_info: Optional[ThorHubAccountInfo]) -> bool:
    return account_info is not None and account_info.is_anonymous_tier


def _normalize_tier(value: object) -> str:
    """Tier claims arrive verbatim from the JWT claim or the account payload, neither of which
    strips or casefolds. Compare them normalized so casing or padding can never turn the
    anonymous tier into a registered one."""
    return value.strip().lower() if isinstance(value, str) else ""


@dataclass(frozen=True)
class ThorHubAccountInfo:
    logged_in: bool
    source: ThorHubAccountInfoSource
    fresh: bool
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    org_slug: Optional[str] = None
    org_name: Optional[str] = None
    client_id: Optional[str] = None
    product_id: Optional[str] = None
    portal_base_url: Optional[str] = None
    inference_base_url: Optional[str] = None
    inference_credential_present: bool = False
    credential_source: Optional[str] = None
    expires_at: Optional[datetime] = None
    email: Optional[str] = None
    subscription: Optional[ThorHubSubscriptionInfo] = None
    paid_service_access: Optional[bool] = None
    paid_service_access_info: Optional[ThorHubPaidServiceAccessInfo] = None
    tool_access: Optional[ThorHubToolAccessInfo] = None
    # Portal ``usage_window`` (account API only): None for every account not on a usage-window plan.
    usage_window: Optional[ThorHubUsageWindowInfo] = None
    raw_claims: Optional[dict[str, Any]] = None
    raw_account: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    # NAS account tier claim; ``"anonymous"`` is the free tier (no ThorHub account behind it).
    account_tier: Optional[str] = None
    # Portal ``managed_tools`` (JWT claim and account API): the portal has enabled connectors for
    # this account. ``None`` = the portal did not say (a token minted before the claim shipped).
    managed_tools: Optional[bool] = None

    @property
    def is_paid(self) -> bool:
        return self.paid_service_access is True

    @property
    def is_anonymous_tier(self) -> bool:
        """The free tier: no Thor account, so no billing, credits, or entitlement to speak of.
        Compared case- and whitespace-insensitively — the claim is wire data."""
        return _normalize_tier(self.account_tier) == _ANON_ACCOUNT_TIER

    @property
    def is_free_tier(self) -> bool:
        return self.paid_service_access is False

    @property
    def tool_gateway_entitled(self) -> bool:
        """ThorHub has no managed tool gateway, so nothing is entitled through it."""
        return False

    def tool_gateway_entitled_for(self, category: str) -> bool:
        """ThorHub has no managed tool gateway; vendor categories need their own key."""
        return False

    @property
    def managed_tools_rolled_out(self) -> bool:
        """ThorHub has no managed connectors."""
        return False


def thorhub_billing_url(account_info: Optional[ThorHubAccountInfo] = None) -> str:
    """ThorHub member portal URL (ThorHub has no /billing page)."""
    base = account_info.portal_base_url if account_info is not None else None
    if not _nonblank(base):
        base = THORHUB_BASE_URL
    return f"{base.rstrip('/')}/portal"


def thorhub_topup_url(account_info: Optional[ThorHubAccountInfo] = None) -> str:
    """ThorHub top-up URL.

    Dulu: portal ThorHub ``{base}/billing?topup=open`` (portal .local sudah mati).
    Sekarang: halaman top-up ThorHub ``/beli/topup`` — kuota ditambah ke key yang
    sama dan masa aktif diperpanjang 25 hari.
    """
    return "https://llm.thormarket.site/beli/topup"


def format_usage_window_block_guidance(account_info: Optional[ThorHubAccountInfo]) -> Optional[str]:
    """Next step after a usage-window 402: the credits step from :func:`agent.plan_limits.credits_action`
    (turn on Keep going, add credits, or both), plus the auto top-up nudge when it is off. None for every
    account not on a usage-window plan, so the credit-grant guidance is unchanged. A paused plan points
    at the card, not at a top-up."""
    window = getattr(account_info, "usage_window", None) if account_info is not None else None
    # A partial/empty block is not a window plan (same completeness rule as the credits seed).
    from agent.credits_tracker import _window_seed_fields
    if _window_seed_fields(window) is None:
        return None
    if paused := getattr(window, "paused_reason", None):
        # A paused plan bills credits whatever the setting says: no credits is why this 402 came.
        from agent.usage_gauges import paused_for_payment
        fix = "Update your card to restore included usage" if paused_for_payment(paused) else "Included usage is paused"
        return f"{fix}, or add credits to keep going now: {thorhub_billing_url(account_info)}"
    from agent.plan_limits import ADD_CREDITS_AND_KEEP_GOING, USE_CREDITS, credits_action
    purchased = getattr(account_info.paid_service_access_info, "purchased_credits_remaining", None)
    action = credits_action(getattr(window, "keep_going_on_credits", None),
                            int(purchased * 1_000_000) if isinstance(purchased, (int, float)) else None)
    if action == USE_CREDITS:
        return f"Turn on Keep going in /topup to use your credits now: {thorhub_billing_url(account_info)}"
    if action == ADD_CREDITS_AND_KEEP_GOING:
        # With the setting off the gateway refuses whatever the balance, so a top-up alone won't do.
        return f"Add credits and turn on Keep going in /topup to keep going now: {thorhub_billing_url(account_info)}"
    lines = [f"Add credits to keep going now: {thorhub_topup_url(account_info)}"]
    if getattr(window, "auto_top_up_enabled", None) is False:
        lines.append("Turn on auto top-up in the same place so this doesn't stop you next time.")
    return "\n".join(lines)


def format_thorhub_entitlement_message(
    account_info: Optional[ThorHubAccountInfo], *, capability: str = "this feature",
    include_refresh_hint: bool = True, coverage_category: Optional[str] = None,
    in_chat: bool = False,
) -> Optional[str]:
    """User-facing guidance for a missing ThorHub entitlement; ``None`` when entitled.

    ThorHub covers LLM calls only: a configured key is entitled to them, and no
    key (or an anonymous tier) is not. A ``coverage_category`` is never covered —
    vendor tools need the vendor's own key.
    """
    if _is_anonymous_tier(account_info):
        return FREE_TIER_NEEDS_ACCOUNT_CHAT if in_chat else FREE_TIER_NEEDS_ACCOUNT
    billing_url = thorhub_billing_url(account_info)

    if coverage_category is not None:
        return (
            f"{capability} isn't included with ThorHub — ThorHub covers LLM calls only. "
            f"Configure the vendor's own API key (run `thor tools`) to use it directly."
        )
    if account_info is None:
        return (
            f"Thor could not verify your ThorHub key, so {capability} is unavailable. "
            f"Set THORHUB_API_KEY or add a key with `thor auth add thor`, or check your balance at {billing_url}."
        )
    if not account_info.logged_in:
        return (
            f"Log in to ThorHub to use {capability}: set THORHUB_API_KEY or run `thor auth add thor`. "
            f"Top up at {thorhub_topup_url(account_info)}."
        )
    if account_info.paid_service_access is None:
        detail = f"Thor could not verify your ThorHub balance, so {capability} is unavailable."
        if account_info.error:
            detail += f" Account lookup failed: {account_info.error}."
        if include_refresh_hint:
            detail += " Run `thor model` to refresh your session."
        return detail + f" Check your balance at {billing_url}."
    if account_info.paid_service_access is False:
        message = _no_paid_access_message(account_info, capability, billing_url, in_chat=in_chat)
        if include_refresh_hint and not account_info.fresh:
            message += " If you recently bought tokens, run `thor model` to refresh Thor."
        return message
    return None


def _no_paid_access_message(
    account_info: ThorHubAccountInfo, capability: str, billing_url: str, *, in_chat: bool = False,
) -> str:
    if _is_anonymous_tier(account_info):
        return FREE_TIER_NEEDS_ACCOUNT_CHAT if in_chat else FREE_TIER_NEEDS_ACCOUNT
    access = account_info.paid_service_access_info or ThorHubPaidServiceAccessInfo()
    active, paid = access.has_active_subscription, access.active_subscription_is_paid
    labelled = (
        ("usable", access.total_usable_credits),
        ("subscription", access.subscription_credits_remaining),
        ("purchased", access.purchased_credits_remaining),
    )
    parts = [f"{label} ${amount:.2f}" for label, amount in labelled if amount is not None]
    credit_detail = f" ({', '.join(parts)})" if parts else ""
    if access.member_spend_cap_exceeded:
        cap, spent = access.member_spend_cap_usd, access.member_spend_usd
        cap_detail = ""
        if cap is not None and spent is not None:
            cap_detail = f" Your organisation's per-member spend cap is ${cap:.2f} and you've spent ${spent:.2f} of it."
        elif cap is not None:
            cap_detail = f" Your organisation's per-member spend cap is ${cap:.2f}."
        return (
            f"Your ThorHub access is paused because you've exceeded the per-member spend cap set by "
            f"your organisation.{cap_detail}{credit_detail} Ask your organisation admin to raise the "
            f"member spend cap at {billing_url}, then run `thor model` to refresh."
        )
    if active and paid:
        return (
            f"Your ThorHub tokens are exhausted{credit_detail}, so {capability} is unavailable. "
            f"Top up at {billing_url}."
        )
    if active and paid is False:
        return (
            f"Your current ThorHub key does not include paid service access, "
            f"so {capability} is unavailable. Top up at {billing_url}."
        )
    if active is False:
        return (
            f"Your ThorHub key has no usable tokens{credit_detail}, "
            f"so {capability} is unavailable. Top up at {billing_url}."
        )
    return (
        f"Your ThorHub key has no usable tokens{credit_detail}, so "
        f"{capability} is unavailable. Top up at {billing_url}."
    )


def reset_thorhub_account_info_cache() -> None:
    """Clear the short-lived account-info cache used by tests."""
    global _account_info_cache, _account_info_identity
    _account_info_cache = None
    _account_info_identity = None


def get_thorhub_account_info(*, force_fresh: bool = False, min_jwt_ttl_seconds: int = 60) -> ThorHubAccountInfo:
    """Normalized ThorHub account snapshot.

    The identity is the static ``sk-thor-...`` key: ``logged_in`` = a key is
    configured, ``paid_service_access`` = the balance read succeeded (the key
    is a bought token package). The balance is cached for 60s; ``force_fresh``
    bypasses the cache. ``min_jwt_ttl_seconds`` is accepted for call-site
    compatibility and ignored (there is no JWT to expire).
    """
    global _account_info_cache, _account_info_identity
    key = thorhub_api_key()
    if not key:
        return ThorHubAccountInfo(logged_in=False, source="none", fresh=False, portal_base_url=THORHUB_BASE_URL)
    identity = _account_identity(key)
    if not force_fresh:
        with _ACCOUNT_INFO_CACHE_LOCK:
            cached = _account_info_cache
        if cached is not None:
            cached_key, cached_at, info = cached
            if cached_key == identity and (time.monotonic() - cached_at) < _ACCOUNT_INFO_CACHE_TTL:
                return info
    try:
        balance = fetch_thorhub_balance()
    except Exception as exc:
        return _error_info(error=exc, logged_in=True, portal_base_url=THORHUB_BASE_URL)
    if balance is None:
        info = ThorHubAccountInfo(
            logged_in=True, source="api_key", fresh=False,
            portal_base_url=THORHUB_BASE_URL, inference_base_url=THORHUB_API_BASE_URL,
            inference_credential_present=True, credential_source="thorhub_key",
            paid_service_access=None, error="balance_unavailable",
        )
    else:
        info = ThorHubAccountInfo(
            logged_in=True, source="api_key", fresh=True,
            portal_base_url=THORHUB_BASE_URL, inference_base_url=THORHUB_API_BASE_URL,
            inference_credential_present=True, credential_source="thorhub_key",
            paid_service_access=True,
            paid_service_access_info=ThorHubPaidServiceAccessInfo(
                allowed=True, paid_access=True,
                total_usable_credits=_coerce_num(balance.get("tokens_remaining"), float),
            ),
            raw_account=balance if isinstance(balance, dict) else None,
        )
    with _ACCOUNT_INFO_CACHE_LOCK:
        _account_info_cache = (identity, time.monotonic(), info)
        _account_info_identity = identity
    return info


def thorhub_policy_present() -> Optional[bool]:
    """ThorHub has no org model/provider policy, so this is always unknown (None)."""
    return None


def cached_thorhub_account_info(*, any_age: bool = False) -> Optional[ThorHubAccountInfo]:
    """The account snapshot in the 60s cache, or None when empty/expired. Never a fresh fetch, never raises —
    for UI chrome that must not add a round trip (the pickers) after a flow has already fetched the account.
    ``any_age`` returns the last snapshot even past the TTL, for callers that read only the plan's shape
    (window or not, featured models), which rarely changes."""
    try:
        with _ACCOUNT_INFO_CACHE_LOCK:
            cached, identity = _account_info_cache, _account_info_identity
        if cached is None:
            return None
        _, cached_at, info = cached
        # Expiry first: it is free, while the identity check reads the auth store.
        if not any_age and (time.monotonic() - cached_at) >= _ACCOUNT_INFO_CACHE_TTL:
            return None
        # Another login, org or portal never reads this snapshot; a refreshed token for the same one does.
        if identity is None or identity != _current_account_identity():
            return None
        return info
    except Exception:
        logging.getLogger(__name__).debug("Cached Thor account info unreadable", exc_info=True)
        return None


def _account_identity(key: str, portal_base_url: Optional[str] = None) -> str:
    """ThorHub base + the key's hash (stable; a static key never refreshes)."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"{portal_base_url or THORHUB_BASE_URL}:{digest}"


def _current_account_identity() -> Optional[str]:
    """``_account_identity`` for the configured ThorHub key. None when no key is set."""
    key = thorhub_api_key()
    if not key:
        return None
    return _account_identity(key)


def thorhub_policy_notice(*, removed: bool) -> str:
    """One-line notice for a list the org's policy narrowed, else ``""``.

    Blocked models are omitted, which reads as "unsupported"; this says which it is without
    enumerating them. ``removed`` must reflect whether the filter actually dropped anything — the
    catalog read fails open, so the claim alone would label a full list as filtered.
    """
    if not removed or thorhub_policy_present() is not True:
        return ""
    return (
        "Your organization restricts which models are available — "
        "models outside its policy are not listed."
    )


def stored_token_account_info() -> Optional[ThorHubAccountInfo]:
    """The ThorHub account for the configured key as it is: None when no key is
    configured. Never forces a fetch beyond the 60s cache: a balance read for a
    session on another provider must not touch the ThorHub credential."""
    if not thorhub_api_key():
        return None
    return get_thorhub_account_info()


def _coerced_dataclass(cls, value: Any):
    """Build ``cls`` from a payload dict (field names = payload keys), coercing by declared type."""
    return cls(**{f.name: _COERCERS[f.type](value.get(f.name)) for f in fields(cls)}) if isinstance(value, dict) else None


def _error_info(
    *, error: object, logged_in: bool, portal_base_url: Optional[str] = None,
    raw_account: Optional[dict[str, Any]] = None, account_tier: Optional[str] = None,
) -> ThorHubAccountInfo:
    """A failed-lookup snapshot. ``account_tier`` is carried through when the caller still holds the
    stored state, so a guest whose lookup failed still gets the "needs a ThorHub account" copy rather
    than billing or re-login guidance."""
    return ThorHubAccountInfo(
        logged_in=logged_in, source="error", fresh=False, portal_base_url=portal_base_url,
        raw_account=raw_account, error=str(error), account_tier=account_tier,
    )


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_iso_timestamp(value: Any) -> Optional[float]:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return None


def _coerce_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _coerce_bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _coerce_num(value: Any, cast):
    """``cast(value)`` or None; bools and None are rejected, not coerced."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _coerce_str_tuple(value: Any) -> Optional[tuple[str, ...]]:
    """A JSON array of non-empty strings → tuple (order kept, non-strings dropped); anything else → None."""
    if not isinstance(value, list):
        return None
    return tuple(v for v in value if isinstance(v, str) and v)


def _parse_gauges(value: Any):
    from agent.usage_gauges import parse_gauges

    return parse_gauges(value)


# Annotations are strings (``from __future__ import annotations``).
_COERCERS = {
    "Optional[str]": _coerce_str,
    "Optional[bool]": _coerce_bool,
    "Optional[int]": lambda v: _coerce_num(v, int),
    "Optional[float]": lambda v: _coerce_num(v, float),
    "Optional[tuple[str, ...]]": _coerce_str_tuple,
    "Optional[tuple[Any, ...]]": lambda v: _parse_gauges(v),
}
