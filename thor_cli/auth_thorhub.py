"""ThorHub auth: a static ``sk-thor-...`` API key, nothing else.

Replaces ``thor_cli.auth_nous`` (deleted in Fase 4 / Commit D). The only credential
is a static ThorHub key — ``THORHUB_API_KEY`` env or auth-store provider ``thor``
(legacy provider ``nous`` state is accepted as a migration bridge, exactly like
:func:`thor_cli.thorhub_account.thorhub_api_key`).

There is deliberately no device-code login, no token refresh, no shared OAuth
store, no JWT/invoke-JWT selection, no credential pool, no quarantine, no
billing-scope step-up, and no guest/free tier: a missing key is a missing key,
and the fix is ``thor auth add thor``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from thor_cli.auth_constants import AuthError, _provider_error_factory

logger = logging.getLogger(__name__)

_thorhub_err = _provider_error_factory("thor")

# Session-validity values reported on the dashboard /api/status. A static key has
# no terminal state discoverable locally: "valid" when a key is configured,
# "unknown" otherwise (a revoked key is discovered at request time, never here).
THORHUB_SESSION_VALID = "valid"
THORHUB_SESSION_UNKNOWN = "unknown"


def _thorhub_http_client(timeout_seconds: float, verify: Any):
    """httpx client for ThorHub calls (same construction the old Nous helper used)."""
    import httpx

    return httpx.Client(timeout=httpx.Timeout(timeout_seconds or 15.0), verify=verify)


def thorhub_portal_base_url(state: Optional[dict[str, Any]] = None) -> str:
    """ThorHub base URL (the portal/member origin). *state* is accepted for
    call-site compatibility and ignored — the URL never came from auth state."""
    from thor_cli.thorhub_account import resolve_thorhub_base_url

    return resolve_thorhub_base_url()


def resolve_thorhub_access_token(
    *,
    timeout_seconds: float = 15.0,
    insecure: Optional[bool] = None,
    ca_bundle: Optional[str] = None,
    refresh_skew_seconds: int = 120,
) -> str:
    """The ThorHub bearer token: the static key itself.

    Drop-in for the old ``resolve_nous_access_token`` at the managed-gateway /
    connectors / account-read call sites. No refresh, no guest minting — a missing
    key raises ``AuthError`` (``thorhub_auth_missing``, relogin) instead of
    returning a guest token.
    """
    from thor_cli.thorhub_account import thorhub_api_key

    key = thorhub_api_key()
    if not key:
        raise _thorhub_err(
            "ThorHub key not configured — run `thor auth add thor` or set THORHUB_API_KEY.",
            "thorhub_auth_missing", relogin=True)
    return key


def resolve_thorhub_runtime_credentials(
    *,
    timeout_seconds: float = 15.0,
    insecure: Optional[bool] = None,
    ca_bundle: Optional[str] = None,
    force_refresh: bool = False,
    stale_access_token: Optional[str] = None,
    read_only: bool = False,
) -> dict[str, Any]:
    """ThorHub inference credentials for runtime use.

    Drop-in for the old ``resolve_nous_runtime_credentials``: the same result
    shape, minus expiry (a static key does not expire) and minus the OAuth
    machinery. ``force_refresh`` / ``stale_access_token`` / TLS kwargs are
    accepted and ignored — there is nothing to refresh.
    """
    from thor_cli.auth import _auth_file_path
    from thor_cli.thorhub_account import resolve_thorhub_base_url, thorhub_api_key

    key = thorhub_api_key()
    if not key:
        raise _thorhub_err(
            "ThorHub key not configured — run `thor auth add thor` or set THORHUB_API_KEY.",
            "thorhub_auth_missing", relogin=True)
    base_url = resolve_thorhub_base_url()
    return {
        "provider": "thor",
        "base_url": f"{base_url.rstrip('/')}/v1",
        "api_key": key,
        "key_id": None,
        "expires_at": None,
        "expires_in": None,
        "source": "thorhub_key",
        "auth_path": "thorhub_key",
        "state_path": str(_auth_file_path()),
    }


def get_thorhub_auth_status_local() -> dict[str, Any]:
    """Refresh-free ThorHub auth snapshot for read-only display surfaces.

    ``logged_in`` = a key is configured (env or auth store). Never touches the
    network and never exposes the key.
    """
    from thor_cli.auth import _auth_file_path, get_provider_auth_state
    from thor_cli.thorhub_account import resolve_thorhub_base_url, thorhub_api_key

    key = thorhub_api_key()
    base_url = resolve_thorhub_base_url()
    try:
        state = get_provider_auth_state("thor") or get_provider_auth_state("nous")
    except Exception:
        state = None
    return {
        "logged_in": bool(key),
        "provider": "thor",
        "has_api_key": bool(key),
        "source": "api_key" if key else "none",
        "portal_base_url": base_url,
        "inference_base_url": f"{base_url.rstrip('/')}/v1",
        "inference_credential_present": bool(key),
        "auth_store": str(_auth_file_path()),
        "state_path": str(_auth_file_path()),
        "state_source": "auth_store" if state else "none",
    }


def get_thorhub_session_validity() -> str:
    """Classify the ThorHub session for the dashboard /api/status probe.

    Local auth state only; never resolves or refreshes. A static key is either
    configured ("valid") or not ("unknown") — there is no terminal state.
    """
    from thor_cli.thorhub_account import thorhub_api_key

    try:
        return THORHUB_SESSION_VALID if thorhub_api_key() else THORHUB_SESSION_UNKNOWN
    except Exception:
        return THORHUB_SESSION_UNKNOWN


def fetch_thorhub_models(
    *,
    inference_base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout_seconds: float = 15.0,
    verify: bool | str = True,
) -> list[str]:
    """Fetch available model IDs from the ThorHub inference API."""
    from thor_cli.thorhub_account import resolve_thorhub_base_url, thorhub_api_key

    base_url = (inference_base_url or resolve_thorhub_base_url()).rstrip("/")
    key = api_key or thorhub_api_key()
    if not key:
        raise _thorhub_err(
            "ThorHub key not configured — run `thor auth add thor` or set THORHUB_API_KEY.",
            "thorhub_auth_missing", relogin=True)
    with _thorhub_http_client(timeout_seconds, verify) as client:
        response = client.get(
            f"{base_url}/v1/models" if not base_url.endswith("/v1") else f"{base_url}/models",
            headers={"Authorization": f"Bearer {key}"})
    if response.status_code != 200:
        description = f"/models request failed with status {response.status_code}"
        try:
            err = response.json()
            description = str(err.get("error_description") or err.get("error") or description)
        except Exception as exc:
            logger.debug("Could not parse error response JSON: %s", exc)
        raise _thorhub_err(description, "models_fetch_failed")
    data = response.json().get("data")
    if not isinstance(data, list):
        return []
    model_ids: list[str] = []
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else None
        if isinstance(model_id, str) and model_id.strip():
            # Hanya model yang gateway-nya benar-benar layani (enabled + available).
            # Entri nonaktif ada di listing tapi tidak bisa dipakai — dan dokumentasi
            # di llm.thormarket.site pun hanya menampilkan yang aktif. Flag yang
            # tidak ada berarti gateway lama: anggap tersedia agar tidak ada yang
            # hilang diam-diam.
            if isinstance(item, dict) and (
                not item.get("enabled", True) or not item.get("available", True)
            ):
                continue
            model_ids.append(model_id.strip())
    return sorted(set(model_ids))


def persist_thorhub_credentials(creds: dict[str, Any], *, label: Optional[str] = None) -> Path:
    """Persist a ThorHub key as the singleton provider state.

    ``creds`` carries ``api_key`` (a raw key string is also accepted). Only the
    key is stored — no OAuth tokens, no shared store, no pool entry.
    """
    from thor_cli.auth import _save_active_provider_state

    key = creds.get("api_key") if isinstance(creds, dict) else None
    if not key and isinstance(creds, dict):
        key = creds.get("key")
    if not isinstance(key, str) or not key.strip():
        raise _thorhub_err("No ThorHub API key to persist.", "thorhub_auth_missing", relogin=True)
    state: dict[str, Any] = {"api_key": key.strip()}
    if label and str(label).strip():
        state["label"] = str(label).strip()
    return _save_active_provider_state("thor", state)
