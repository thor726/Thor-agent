"""Managed-tool gateway helpers (ThorHub era).

ThorHub does not proxy third-party vendor tools (fal, Modal, Firecrawl,
Perplexity, OpenAI audio, Krea, browser-use): there is no managed vendor
gateway to resolve. Vendor tools work only with their own direct API keys,
so the ``resolve_*`` helpers always report "not available" and call sites
fall back to their direct-key paths.

The ThorHub LLM key itself is a static ``sk-thor-...`` key: read it with
:func:`peek_thorhub_api_key` / :func:`read_thorhub_api_key` (``THORHUB_API_KEY``
or the ``thor`` auth-store provider). There is no refresh: the key is static,
and the guest connectors-token leg was removed with the guest tier.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from tools.tool_backend_helpers import managed_thorhub_tools_enabled  # re-export: patch target for tool tests

logger = logging.getLogger(__name__)

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
    migration bridge (the ``thor`` provider still aliases ``nous*``).
    """
    try:
        from thor_cli.auth import get_provider_auth_state

        for provider in ("thor", "nous"):
            state = get_provider_auth_state(provider)
            if not isinstance(state, dict):
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


def peek_thorhub_api_key() -> Optional[str]:
    """Cheap ThorHub key probe: env override or static ThorHub key — no expiry
    check and no network."""
    try:
        from thor_cli.thorhub_account import thorhub_api_key

        return _read_user_token_override() or _clean(thorhub_api_key())
    except Exception:
        return None


def read_thorhub_api_key() -> Optional[str]:
    """Read the ThorHub API key: env override, else the static ThorHub key.
    There is no refresh and no fallback — with no key configured the answer is None.
    """
    if explicit := _read_user_token_override():
        return explicit
    try:
        from thor_cli.thorhub_account import thorhub_api_key

        return _clean(thorhub_api_key())
    except Exception:
        return None


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
