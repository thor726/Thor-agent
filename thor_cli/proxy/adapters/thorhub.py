"""ThorHub upstream adapter (static API key, no OAuth)."""

from __future__ import annotations

import threading
from typing import Any, Dict, FrozenSet, Optional

from thor_cli.auth_thorhub import resolve_thorhub_runtime_credentials
from thor_cli.proxy.adapters.base import UpstreamAdapter, UpstreamCredential

# Endpoints ThorHub (OpenAI-compatible /v1) serves; anything else is a 404 so stray
# clients cannot leak odd requests upstream.
_ALLOWED_PATHS: frozenset[str] = frozenset({"/chat/completions", "/completions", "/embeddings", "/models"})


class ThorHubAdapter(UpstreamAdapter):
    """Proxy upstream for the ThorHub inference API."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "thor"

    @property
    def display_name(self) -> str:
        return "ThorHub"

    @property
    def allowed_paths(self) -> frozenset[str]:
        return _ALLOWED_PATHS

    def is_authenticated(self) -> bool:
        try:
            resolve_thorhub_runtime_credentials()
        except Exception:
            return False
        return True

    def get_credential(self) -> UpstreamCredential:
        return self._get_credential()

    def get_retry_credential(
        self, *, failed_credential: UpstreamCredential, status_code: int
    ) -> Optional[UpstreamCredential]:
        # A static key has nothing to refresh: a 401 means the key is revoked, and retrying
        # with the same key cannot succeed.
        return None

    def _get_credential(self) -> UpstreamCredential:
        with self._lock:
            try:
                creds = resolve_thorhub_runtime_credentials()
            except Exception as exc:
                raise RuntimeError(
                    f"ThorHub credentials unavailable: {exc}. "
                    "Run `thor auth add thor` or set THORHUB_API_KEY."
                ) from exc
            runtime_key = creds.get("api_key")
            if not runtime_key:
                raise RuntimeError(
                    "ThorHub returned no usable API key. "
                    "Run `thor auth add thor` or set THORHUB_API_KEY."
                )
            base_url = (creds.get("base_url") or "https://llm.thormarket.site/v1").rstrip("/")
            return UpstreamCredential(bearer=runtime_key, base_url=base_url, expires_at=None)


__all__ = ["ThorHubAdapter"]
