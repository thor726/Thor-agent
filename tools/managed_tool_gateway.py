"""Managed-tool gateway helpers (ThorHub era).

ThorHub does not proxy third-party vendor tools (fal, Modal, Firecrawl,
Perplexity, OpenAI audio, Krea, browser-use): there is no managed vendor
gateway to resolve. Vendor tools work only with their own direct API keys,
so the ``resolve_*`` helpers always report "not available" and call sites
fall back to their direct-key paths.

The ThorHub LLM key itself is a static ``sk-thor-...`` key: read it with
:func:`peek_thorhub_api_key` / :func:`read_thorhub_api_key` (``THORHUB_API_KEY``
or the ``thor`` auth-store provider). The only refresh left is the legacy
guest connectors-token leg inside those two readers; it is removed with the
guest tier.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from tools.tool_backend_helpers import managed_thorhub_tools_enabled  # re-export: patch target for tool tests

logger = logging.getLogger(__name__)

_NOUS_ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 120  # legacy guest-token refresh skew; removed with the guest tier


@dataclass(frozen=True)
class ManagedToolGatewayConfig:
    vendor: str
    gateway_origin: str
    api_key: str
    managed_mode: bool


def _clean(value: object) -> Optional[str]:
    """*value* stripped when it is a non-blank string, else None."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _read_thorhub_provider_state() -> Optional[dict]:
    """The profile's ThorHub auth state, or None.

    Provider ``thor`` first; legacy provider ``nous`` state is accepted as a
    migration bridge (the ``thor`` provider still aliases ``nous*``). A guest
    state counts only while guests are allowed: with ``nous.guest: false`` it
    is invisible here, so no cached or refreshed token of it is ever attached
    to a request.
    """
    try:
        from thor_cli.auth import get_provider_auth_state
        from thor_cli.anon_auth import guest_allowed, is_guest_state

        for provider in ("thor", "nous"):
            state = get_provider_auth_state(provider)
            if not isinstance(state, dict):
                continue
            if is_guest_state(state) and not guest_allowed():
                continue
            return state
    except Exception:
        pass
    return None


def _read_user_token_override() -> Optional[str]:
    """Read the TOOL_GATEWAY_USER_TOKEN override through the secret scope. Scope verdict is authoritative
    when installed (a scoped miss must NOT borrow the process env under multiplex); ``os.environ`` only
    when unscoped. Any non-UnscopedSecretError failure propagates -- a failed scoped read must never
    silently borrow the ambient env."""
    from agent.secret_scope import UnscopedSecretError, get_secret

    try:
        explicit = get_secret("TOOL_GATEWAY_USER_TOKEN")
    except UnscopedSecretError:
        explicit = os.getenv("TOOL_GATEWAY_USER_TOKEN")
    return _clean(explicit)


def _replace_dead_guest_token(dead_state: dict, code: str = "anon_credential_dead") -> Optional[str]:
    from thor_cli.anon_auth import ANON_ACCOUNT_LOCKED, clear_dead_guest, ensure_portal_identity
    from thor_cli.auth import resolve_nous_access_token

    clear_dead_guest(code, dead_token=dead_state.get("anon_token"))
    # Same rule as inference: a locked account is retired but never silently replaced.
    if code == ANON_ACCOUNT_LOCKED:
        return None
    try:
        if ensure_portal_identity(explicit=True) is None:
            return None
        return _clean(resolve_nous_access_token(refresh_skew_seconds=_NOUS_ACCESS_TOKEN_REFRESH_SKEW_SECONDS))
    except Exception as exc:
        logger.debug("Nous free tier replacement after a retired credential failed: %s", exc)
        return None


def peek_thorhub_api_key() -> Optional[str]:
    """Cheap ThorHub key probe: env override, static ThorHub key, or the cached
    guest connectors token — no expiry check and no network.

    The guest-token leg is legacy (the connectors guest tier is removed with
    the guest identity machinery); availability scans must stay off the
    synchronous refresh path (:func:`read_thorhub_api_key`).
    """
    try:
        from thor_cli.anon_auth import held_connectors_token
        from thor_cli.thorhub_account import thorhub_api_key

        return (
            _read_user_token_override()
            or _clean(thorhub_api_key())
            or _clean(held_connectors_token(_read_thorhub_provider_state()))
        )
    except Exception:
        return None


def read_thorhub_api_key() -> Optional[str]:
    """Read the ThorHub API key, or the guest connectors token as a legacy fallback.

    Order: env override, static ThorHub key, then the guest path — a fresh held
    connectors token, else a refresh via the auth core (the retired-credential
    rule replaces a dead guest once, shared with inference). The guest leg is
    legacy and is removed with the guest tier; with no ThorHub key and no guest
    identity there is no bearer <redacted> answer is None.
    """
    if explicit := _read_user_token_override():
        return explicit
    try:
        from thor_cli.thorhub_account import thorhub_api_key

        if static := _clean(thorhub_api_key()):
            return static
    except Exception:
        pass
    provider = _read_thorhub_provider_state() or {}
    if not provider:
        return None
    from thor_cli.anon_auth import held_connectors_token

    if fresh_token := _clean(held_connectors_token(
            provider, skew_seconds=_NOUS_ACCESS_TOKEN_REFRESH_SKEW_SECONDS)):
        return fresh_token
    cached_token = _clean(provider.get("access_token"))
    try:
        from thor_cli.auth import resolve_nous_access_token

        if refreshed_token := _clean(resolve_nous_access_token(
            refresh_skew_seconds=_NOUS_ACCESS_TOKEN_REFRESH_SKEW_SECONDS)):
            return refreshed_token
    except Exception as exc:
        # Same dead-credential rule as inference (one place decides it: anon_auth): a retired free-tier
        # identity is replaced once, here, instead of handing back its stale token forever.
        from thor_cli.anon_auth import AnonCredentialDead

        if isinstance(exc, AnonCredentialDead):
            return _replace_dead_guest_token(provider, str(exc.code or "anon_credential_dead"))
        logger.debug("ThorHub API key refresh failed: %s", exc)
    return cached_token


def build_vendor_gateway_url(vendor: str) -> str:
    """Explicit per-vendor gateway URL override (``{VENDOR}_GATEWAY_URL``), or "".

    There is no default managed gateway origin anymore: without an explicit
    override there is nowhere to route a vendor call.
    """
    if explicit := os.getenv(f"{vendor.upper().replace('-', '_')}_GATEWAY_URL", "").strip().rstrip("/"):
        return explicit
    return ""


def resolve_managed_tool_gateway(
    vendor: str, gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None) -> Optional[ManagedToolGatewayConfig]:
    """Explicit override only: a config when ``{VENDOR}_GATEWAY_URL`` (or *gateway_builder*) names an
    origin — a self-hosted gateway the user configured. There is no default managed gateway: without
    an explicit override the answer is None, so vendor tools fall back to their direct-key paths.
    The bearer is the ThorHub key (or *token_reader*'s value); a self-hosted gateway that needs no
    auth simply gets an empty key.
    """
    origin = (gateway_builder or build_vendor_gateway_url)(vendor)
    if not origin:
        return None
    token = (token_reader or peek_thorhub_api_key)()
    if not token:
        return None
    return ManagedToolGatewayConfig(
        vendor=vendor, gateway_origin=origin, api_key=token, managed_mode=True)


def resolve_free_search_gateway(token_reader: Optional[Callable[[], Optional[str]]] = None) -> Optional[ManagedToolGatewayConfig]:
    """Perplexity fast search through an explicitly configured gateway only; ThorHub has no free
    Perplexity route of its own."""
    return resolve_managed_tool_gateway("perplexity", token_reader=token_reader)


def is_managed_tool_gateway_ready(
    vendor: str, gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None) -> bool:
    """True when an explicit gateway origin is configured for *vendor*."""
    return resolve_managed_tool_gateway(vendor, gateway_builder=gateway_builder, token_reader=token_reader) is not None
