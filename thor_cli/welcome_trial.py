"""The desktop's welcome trial — RETIRED with the Nous Portal (Fase 4 debrand).

Free inference on ``nous/welcome`` for a first install only ever existed on the Nous Portal.
ThorHub has no free tier, so the trial can never be claimed: :func:`claim_blocker` always names
the retirement, :func:`claim_desktop_free_tier` raises an honest ``AuthError``, and the
provider/inference predicates answer from the ThorHub key instead.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from thor_cli import anon_auth
from thor_cli.auth_constants import AuthError

logger = logging.getLogger("thor_cli.auth")


def _has_thorhub_identity() -> bool:
    """A ThorHub key is configured (env, auth store, or credential pool)."""
    from thor_cli.thorhub_account import thorhub_api_key

    return bool(thorhub_api_key())


def provider_configured() -> bool:
    """Something carries inference: a key, a config pin, a sign-in, a host credential."""
    from thor_cli.auth import resolve_provider

    try:
        provider = resolve_provider("auto", skip_free_tier=True)
    except AuthError:  # no_provider_configured
        return False
    return bool(provider)


def inference_available(*, assume_fresh: bool = False) -> bool:
    """Something can carry a first chat on this backend: a configured provider (the trial is gone)."""
    return provider_configured()


def claim_blocker(*, assume_fresh: bool = False, configured: Optional[bool] = None) -> Optional[str]:
    """Why the trial cannot be claimed here — always, because the trial is retired."""
    return "the welcome trial is retired (ThorHub has no free tier)"


def claim_desktop_free_tier(*, assume_fresh: bool = False, force: bool = False) -> Optional[dict[str, Any]]:
    """Claim the trial — retired: nothing to claim when something already carries inference
    (onboarding calls this on every fresh launch, configured or not), otherwise raises an
    honest ``AuthError`` instead of minting a guest."""
    if provider_configured():
        return None
    raise AuthError(
        "The welcome trial is retired — ThorHub has no free tier. "
        "Add a ThorHub key with `thor auth add thor` or set THORHUB_API_KEY.",
        provider="thor", code="thorhub_no_free_tier", relogin_required=False)


def settle_interrupted_claim() -> bool:
    """No interrupted claim can exist anymore (nothing was ever minted)."""
    return False
