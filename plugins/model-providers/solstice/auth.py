"""Solstice sign-in: browser PKCE with a loopback redirect, token exchange and refresh brokered by the
Nous portal (NAS), which holds the confidential client secret.

The Nous Portal is retired, so Solstice has no token broker anymore: every NAS call raises an honest
error telling the user to use ThorHub or another provider. The module shape is kept so
``thor auth add solstice`` fails with that message instead of an import error.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

_CONFIG_PATH = "/api/oauth/gemini-auth/config"
_TOKEN_PATHS = {"authorization_code": "/api/oauth/gemini-auth/exchange", "refresh_token": "/api/oauth/gemini-auth/refresh"}
_TIMEOUT_SECONDS = 30.0


def _err(message: str, code: str, *, relogin: bool = False):
    from thor_cli.auth_constants import AuthError
    return AuthError(f"solstice: {message}", provider="solstice", code=code, relogin_required=relogin)


def _nas_request(method: str, path: str, *, json: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The Nous Portal NAS broker is retired — Solstice cannot sign in anymore."""
    raise _err("Solstice runs on the Nous Portal, which is retired. "
               "Use ThorHub or another provider instead.", "solstice_portal_retired")


def discover_client() -> dict[str, str]:
    """``client_id`` / ``authorize_url`` / ``scope`` NAS serves for the shared Google client."""
    payload = _nas_request("GET", _CONFIG_PATH)
    missing = [k for k in ("client_id", "authorize_url", "scope") if not str(payload.get(k) or "").strip()]
    if missing:
        raise _err(f"Solstice config is missing {', '.join(missing)}.", "solstice_config_invalid")
    return {k: str(payload[k]).strip() for k in ("client_id", "authorize_url", "scope")}


def broker_token_request(grant: Mapping[str, str]) -> Mapping[str, Any]:
    """``OAuthPKCEConfig.token_request``: send the grant to NAS, which adds the client secret.

    NAS folds every Google token-endpoint failure into HTTP 502, so a refresh it rejects is treated as
    a dead grant (re-login) rather than retried against a token Google already refused.
    """
    path = _TOKEN_PATHS[grant["grant_type"]]
    body = {k: v for k, v in grant.items() if k in ("code", "code_verifier", "redirect_uri", "refresh_token")}
    try:
        return _nas_request("POST", path, json=body)
    except Exception as exc:
        if grant["grant_type"] == "refresh_token" and getattr(exc, "code", "") == "solstice_broker_failed":
            raise _err("the stored sign-in was rejected; run `thor auth add solstice` again.",
                       "invalid_grant", relogin=True) from exc
        raise
