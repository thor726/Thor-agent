"""Generic managed-tool gateway helpers for Thor-hosted vendor passthroughs."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from thor_constants import get_thor_home
from tools.tool_backend_helpers import managed_thor_tools_enabled

logger = logging.getLogger(__name__)

_DEFAULT_TOOL_GATEWAY_DOMAIN = "thor-agent.local"
_DEFAULT_TOOL_GATEWAY_SCHEME = "https"
_THOR_PORTAL_ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 120


@dataclass(frozen=True)
class ManagedToolGatewayConfig:
    vendor: str
    gateway_origin: str
    thor_user_token: str
    managed_mode: bool


def _clean(value: object) -> Optional[str]:
    """*value* stripped when it is a non-blank string, else None."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def auth_json_path():
    """Return the Thor auth store path, respecting THOR_HOME overrides."""
    return get_thor_home() / "auth.json"


def _read_thor_provider_state() -> Optional[dict]:
    """The profile's Thor state, or None. A free-tier identity counts only while guests are allowed:
    with ``thor.guest: false`` it is invisible here, so no cached or refreshed token of it is ever
    attached to a request.

    Resolves through the same profile-then-global-root fallback every other credential reader
    uses: a profile created with ``share_auth`` has no ``auth.json`` of its own and signs in with
    the root identity. Reading only ``THOR_HOME/auth.json`` made that profile look signed out to
    the connector gate alone, so ``manage_connections`` vanished from its tool list."""
    try:
        from thor_cli.auth import get_provider_auth_state

        thor_provider = get_provider_auth_state("thor")
        if not isinstance(thor_provider, dict):
            return None
        from thor_cli.anon_auth import guest_allowed, is_guest_state

        if is_guest_state(thor_provider) and not guest_allowed():
            return None
        return thor_provider
    except Exception:
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


def peek_thor_access_token() -> Optional[str]:
    """Cheap token probe: env override or cached auth-store token, no expiry check and no network —
    availability scans must stay off the synchrothor OAuth refresh path (:func:`read_thor_access_token`)."""
    from thor_cli.anon_auth import held_connectors_token

    return _read_user_token_override() or _clean(held_connectors_token(_read_thor_provider_state()))


def read_thor_access_token() -> Optional[str]:
    """Read a Thor Subscriber OAuth access token from auth store or env override.

    A read: with no Thor identity there is no bearer and the answer is None. The free-tier identity
    is created by the boot bootstrap or the first hosted connector action, never on a token-read
    path (NS-845 Q1.2). A retired free-tier credential IS replaced here, once: that is the explicit
    dead-credential rule, shared with inference.
    """
    if explicit := _read_user_token_override():
        return explicit
    thor_provider = _read_thor_provider_state() or {}
    if not thor_provider:
        return None
    from thor_cli.anon_auth import held_connectors_token

    if fresh_token := _clean(held_connectors_token(thor_provider, skew_seconds=_THOR_PORTAL_ACCESS_TOKEN_REFRESH_SKEW_SECONDS)):
        return fresh_token
    cached_token = peek_thor_access_token()
    try:
        from thor_cli.auth import resolve_thor_access_token

        if refreshed_token := _clean(resolve_thor_access_token(refresh_skew_seconds=_THOR_PORTAL_ACCESS_TOKEN_REFRESH_SKEW_SECONDS)):
            return refreshed_token
    except Exception as exc:
        # Same dead-credential rule as inference (one place decides it: anon_auth): a retired free-tier
        # identity is replaced once, here, instead of handing back its stale token forever.
        from thor_cli.anon_auth import AnonCredentialDead

        if isinstance(exc, AnonCredentialDead):
            return _replace_dead_guest_token(thor_provider, str(exc.code or "anon_credential_dead"))
        logger.debug("Thor access token refresh failed: %s", exc)
    return cached_token


def _replace_dead_guest_token(dead_state: dict, code: str = "anon_credential_dead") -> Optional[str]:
    from thor_cli.anon_auth import ANON_ACCOUNT_LOCKED, clear_dead_guest, ensure_portal_identity
    from thor_cli.auth import resolve_thor_access_token

    clear_dead_guest(code, dead_token=dead_state.get("anon_token"))
    # Same rule as inference: a locked account is retired but never silently replaced.
    if code == ANON_ACCOUNT_LOCKED:
        return None
    try:
        if ensure_portal_identity(explicit=True) is None:
            return None
        return _clean(resolve_thor_access_token(refresh_skew_seconds=_THOR_PORTAL_ACCESS_TOKEN_REFRESH_SKEW_SECONDS))
    except Exception as exc:
        logger.debug("Thor free tier replacement after a retired credential failed: %s", exc)
        return None


def get_tool_gateway_scheme() -> str:
    """Return configured shared gateway URL scheme."""
    scheme = os.getenv("TOOL_GATEWAY_SCHEME", "").strip().lower() or _DEFAULT_TOOL_GATEWAY_SCHEME
    if scheme not in {"http", "https"}:
        raise ValueError("TOOL_GATEWAY_SCHEME must be 'http' or 'https'")
    return scheme


def build_vendor_gateway_url(vendor: str) -> str:
    """Return the gateway origin for a specific vendor."""
    if explicit_vendor_url := os.getenv(f"{vendor.upper().replace('-', '_')}_GATEWAY_URL", "").strip().rstrip("/"):
        return explicit_vendor_url
    shared_domain = os.getenv("TOOL_GATEWAY_DOMAIN", "").strip().strip("/") or _DEFAULT_TOOL_GATEWAY_DOMAIN
    return f"{get_tool_gateway_scheme()}://{vendor}-gateway.{shared_domain}"


def _vendor_gateway(vendor: str, gateway_builder, token_reader) -> Optional[ManagedToolGatewayConfig]:
    gateway_origin = (gateway_builder or build_vendor_gateway_url)(vendor)
    thor_user_token = (token_reader or read_thor_access_token)()
    if not gateway_origin or not thor_user_token:
        return None
    return ManagedToolGatewayConfig(vendor=vendor, gateway_origin=gateway_origin, thor_user_token=thor_user_token, managed_mode=True)


def resolve_managed_tool_gateway(
    vendor: str, gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None) -> Optional[ManagedToolGatewayConfig]:
    """Resolve shared managed-tool gateway config for a vendor (entitled accounts only)."""
    if not managed_thor_tools_enabled():
        return None
    return _vendor_gateway(vendor, gateway_builder, token_reader)


def resolve_free_search_gateway(token_reader: Optional[Callable[[], Optional[str]]] = None) -> Optional[ManagedToolGatewayConfig]:
    """Perplexity ``search_type: "fast"`` is served to every Thor identity with no funding check, the
    anonymous guest tier included, so it needs a token this profile may use (guest-disabled and refresh
    rules live in the reader), not paid entitlement or a registered account. Search only: every other
    vendor route goes through :func:`resolve_managed_tool_gateway`."""
    return _vendor_gateway("perplexity", None, token_reader)


def is_managed_tool_gateway_ready(
    vendor: str, gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None) -> bool:
    """True when a gateway URL and a likely-usable Thor token are present. Defaults to
    :func:`peek_thor_access_token` (no OAuth refresh); callers about to make a real request use
    :func:`resolve_managed_tool_gateway` instead."""
    return resolve_managed_tool_gateway(vendor, gateway_builder=gateway_builder, token_reader=token_reader or peek_thor_access_token) is not None
