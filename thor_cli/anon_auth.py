"""Anonymous / guest free tier — RETIRED with the Nous Portal (Fase 4 debrand).

The guest free tier (anonymous minting on the Portal, the ``nous/welcome`` trial, guest JWTs,
the welcome-refusal and model-switch machinery) only ever existed on the Nous Portal, which is
gone. ThorHub has no free tier, no guest minting and no anonymous inference — only static API
keys (``thor auth add thor`` / ``THORHUB_API_KEY``).

This module is kept as a retired shim so the many surfaces that import it (onboarding, the TUI
free-tier RPCs, the agent's error classifier, the credential pool) keep resolving: every guest
predicate answers "no guest", every guest action raises an honest ``AuthError``. The Portal
network code — minting, JWT exchange, refresh, the shared Nous store — is deleted, not moved.

Only :func:`on_local_desktop_backend` keeps a real implementation: it is a platform check (is
this the Desktop app on this machine), not a guest check, and the provider ladder still uses it.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, ContextManager, Iterator, Optional

from thor_cli.auth_constants import AuthError, WELCOME_CLAIM_FLAG

logger = logging.getLogger("thor_cli.auth")

# --- Retired identifiers (kept so imports keep resolving; never routed) -----------------------
ANON_AUTH_METHOD = "anonymous"
ANON_CLIENT_ID = "nas-anonymous"
ANON_ACCOUNT_TIER = "anonymous"
GUEST_MODEL = "nous/welcome"  # retired: the free-tier model id; trial_model() returns "" now
GUEST_NOTICE_FLAG = "guest_notice_shown"  # retired: never set anymore; kept so legacy state can be read
ANON_SECRET_HEADER = "x-anonymous-api-secret"
ANON_SECRET_ENV = "THOR_ANON_API_SECRET"
PREVIEW_FULL_CONNECTORS_ENV = "THOR_PREVIEW_FULL_CONNECTORS"
GUEST_MINT_TIMEOUT_SECONDS = 5.0
FREE_TIER_LABEL = "Thor · free tier"
UPGRADE_HINT = "Run `thor auth add thor` to add your ThorHub key, or /model inside a chat."
FREE_TIER_NOT_SIGNED_IN = (
    "You're not signed in. Add your ThorHub key with `thor auth add thor` "
    "or set THORHUB_API_KEY.")
FREE_TIER_OUTAGE_COPY = (
    "ThorHub is having trouble responding right now. "
    "Check your ThorHub balance at https://llm.thormarket.site/portal.")
EXTRA_WELCOME_HOSTS_ENV = "THOR_EXTRA_WELCOME_HOSTS"


class AnonCredentialDead(AuthError):
    """Kept for import compatibility; never raised anymore (no guest credentials exist)."""


def _retired_err(message: str = "") -> AuthError:
    return AuthError(
        message or "The guest free tier is retired — ThorHub has no free tier. "
        "Add a ThorHub key with `thor auth add thor` or set THORHUB_API_KEY.",
        provider="thor", code="thorhub_no_free_tier", relogin_required=False)


def _anon_err(message: str, code: str, *, retry_after: Optional[float] = None) -> AuthError:
    """An ``AuthError`` for a free-tier failure *code*; terminal-ness is the code's (``ANON_TERMINAL_CODES``)."""
    return AuthError(message, code=code, retry_after=retry_after, retryable=code not in ANON_TERMINAL_CODES)


# --- Free-tier failure codes (kept: surfaces key their copy on them) --------------------------
ANON_GATE_CLOSED = "anon_gate_closed"
ANON_GATE_PAUSED = "anon_gate_paused"
ANON_RATE_LIMITED = "anon_rate_limited"
ANON_POW_REQUIRED = "anon_pow_required"
ANON_ACCOUNT_LOCKED = "anon_account_locked"
ANON_CREDENTIAL_DEAD = "anon_credential_dead"
ANON_UNREACHABLE = "anon_unreachable"
ANON_SERVER_ERROR = "anon_server_error"
ANON_CHALLENGE_REQUIRED = "anon_challenge_required"
ANON_SIGNIN_REQUIRED = "anon_signin_required"
ANON_TERMINAL_CODES = frozenset({
    ANON_GATE_CLOSED, ANON_POW_REQUIRED, ANON_ACCOUNT_LOCKED, ANON_SIGNIN_REQUIRED})
ANON_UNREACHABLE_CODES = frozenset({ANON_UNREACHABLE, ANON_SERVER_ERROR})

_SIGNIN_IS_FREE = "Signing in is free."
ANON_FAILURE_COPY = {
    ANON_GATE_CLOSED: f"This version can't be used without a Thor account. {_SIGNIN_IS_FREE}",
    ANON_GATE_PAUSED: f"Using Thor without signing in is paused for a moment. {_SIGNIN_IS_FREE}",
    ANON_RATE_LIMITED: "Lots of people are getting started right now. Try again in {wait}. "
                       "Signing in is free and skips the wait.",
    ANON_POW_REQUIRED: "The Thor server asked for a proof of work, but that isn't implemented in your "
                       "Agent yet. Sign in with a Thor account to continue.",
    ANON_CHALLENGE_REQUIRED: "Finish the quick check in your browser, then try again.",
    ANON_SIGNIN_REQUIRED: "Free guest access isn't available here. Sign in with a Thor account to continue.",
    ANON_ACCOUNT_LOCKED: f"This session can't continue without signing in. {_SIGNIN_IS_FREE}",
    ANON_CREDENTIAL_DEAD: "Your session ended. A new one starts on its own.",
    ANON_UNREACHABLE: "The Thor service couldn't be reached. Check your internet connection and try again.",
    ANON_SERVER_ERROR: "The Thor service had a hiccup. Try again in a moment.",
}


def friendly_wait(seconds: Any) -> str:
    """A rounded, spoken duration for user copy: "a few seconds", "about a minute", "about 5 minutes",
    "about an hour". Never a raw second count."""
    try:
        total = float(seconds or 0)
    except (TypeError, ValueError):
        return "a few seconds"
    if total <= 10:
        return "a few seconds"
    if total < 90:
        return "about a minute"
    minutes = round(total / 60)
    if minutes < 60:
        return f"about {minutes} minutes"
    hours = round(minutes / 60)
    return "about an hour" if hours == 1 else f"about {hours} hours"


def anon_failure_copy(code: str, *, retry_after: Any = None) -> str:
    """The surface-agnostic sentence for a free-tier failure *code* (``ANON_FAILURE_COPY``)."""
    template = ANON_FAILURE_COPY.get(code) or ANON_FAILURE_COPY[ANON_SERVER_ERROR]
    return template.format(wait=friendly_wait(retry_after if retry_after else 60))


# --- Guest predicates: always "no guest" -------------------------------------------------------
def guest_allowed() -> bool:
    """Guests are retired: always False (the ``nous.guest`` config flag no longer enables anything)."""
    return False


def is_guest_state(state: Any) -> bool:
    return False


def is_anonymous_request(provider: Any, api_key: Any) -> bool:
    return False


def is_anonymous_agent(agent: Any) -> bool:
    return False


def current_nous_state() -> Optional[dict[str, Any]]:
    """The profile's Thor identity — always None now (the legacy ``providers.nous`` state is unread)."""
    return None


def has_guest() -> bool:
    return False


def on_local_desktop_backend() -> bool:
    """This activity is work for the Desktop app on this machine: a request from, or a turn of a chat
    created by, a connection ``process_identity.local_desktop_client`` accepted. Never an SSH, URL or
    cloud backend, a shell the desktop launched, or the gateway's other clients."""
    from thor_cli.process_identity import serves_local_desktop_now
    return serves_local_desktop_now()


def free_inference_active(state: Any = None) -> bool:
    return False


def trial_model() -> str:
    return ""


def has_free_tier_account() -> bool:
    return False


def guest_without_free_tier(state: Any) -> bool:
    return False


def free_tier_route() -> bool:
    return False


WELCOME_HOSTS = frozenset()


def welcome_hosts() -> frozenset[str]:
    return frozenset()


def pin_model_for_route(provider: Any, base_url: Any, model: Any) -> Any:
    return model


def route_can_serve_model(provider: Any, base_url: Any, model: Any) -> bool:
    """ThorHub has no route restrictions: any ThorHub route serves any catalog model.

    The old implementation split the welcome host (free tier only) from the paid host;
    both are gone with the guest tier, so the pool-rotation gate in
    ``agent.client_lifecycle._swap_credential`` must not refuse a swap.
    """
    return True


def route_is_welcome_host(base_url: Any) -> bool:
    return False


def on_free_model(agent: Any, base_url: Any) -> bool:
    return False


def anon_secret() -> str:
    return ""


def _anon_headers() -> dict[str, str]:
    return {}


def _raise_for_anon_status(*args: Any, **kwargs: Any) -> None:
    raise _retired_err()


def mint_request_body() -> dict[str, Any]:
    return {}


def mint_guest(client: Any, portal_base_url: str) -> dict[str, Any]:
    raise _retired_err()


def is_connectors_only(token: Any) -> bool:
    return False


def held_connectors_token(state: Any, *, skew_seconds: Optional[int] = None) -> Optional[str]:
    return None


def exchange_anon_jwt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise _retired_err()


def apply_exchange_to_state(state: dict[str, Any], exchanged: dict[str, Any]) -> None:
    return None


def _portal_base_url() -> str:
    return ""


def _shared_identity_key(state: Any) -> Optional[str]:
    return None


def _mint_locked(client: Any, portal: str, auth_store: dict[str, Any], *args: Any, **kwargs: Any) -> None:
    raise _retired_err()


@dataclass
class MintFailure:
    """Why the last mint for a profile failed and when the next one may run (kept for tests/status)."""

    code: str
    message: str
    retryable: bool
    retry_after: float
    not_before: float
    attempts: int = 1

    def remaining(self) -> float:
        return 0.0 if not self.retryable else max(0.0, round(self.not_before - time.monotonic(), 3))

    def as_payload(self) -> dict[str, Any]:
        return {"error_code": self.code, "error": self.message, "retryable": self.retryable,
                "retry_after": math.ceil(self.remaining()) if self.retryable else 0}


_mint_failures: dict[str, MintFailure] = {}


def _mint_memo_key() -> str:
    from thor_constants import get_thor_home_override, thor_home_key
    return "" if get_thor_home_override() is None else thor_home_key()


def _mint_failure_for_profile() -> Optional[MintFailure]:
    return _mint_failures.get(_mint_memo_key())


def _clear_mint_failure() -> None:
    _mint_failures.pop(_mint_memo_key(), None)


def reset_mint_memo_for_tests() -> None:
    _mint_failures.clear()


def last_mint_failure() -> Optional[dict[str, Any]]:
    failure = _mint_failure_for_profile()
    return failure.as_payload() if failure else None


def classify_mint_exception(exc: BaseException) -> AuthError:
    """Every mint failure as one ``AuthError`` with a code (kept for the sign-in failure path)."""
    if isinstance(exc, AuthError) and exc.code:
        return exc
    transport = (TimeoutError, ConnectionError, OSError)
    code = ANON_UNREACHABLE if isinstance(exc, transport) else ANON_SERVER_ERROR
    wrapped = _anon_err(ANON_FAILURE_COPY[code], code, retry_after=getattr(exc, "retry_after", None))
    wrapped.__cause__ = exc
    return wrapped


def _note_mint_failure(err: AuthError) -> MintFailure:
    failure = MintFailure(code=str(err.code or ANON_SERVER_ERROR), message=str(err),
                          retryable=bool(err.retryable), retry_after=float(err.retry_after or 0.0),
                          not_before=time.monotonic() + float(err.retry_after or 0.0))
    _mint_failures[_mint_memo_key()] = failure
    return failure


def _reconcile_and_provision(*args: Any, **kwargs: Any) -> None:
    raise _retired_err()


def ensure_portal_identity(*args: Any, **kwargs: Any) -> None:
    raise _retired_err()


def refresh_guest_state(state: dict[str, Any], client: Any, *, purpose: str) -> str:
    raise _retired_err()


def clear_dead_guest(reason: str, *, dead_token: Optional[str] = None) -> None:
    return None


def parse_welcome_refusal(body: Any) -> Optional[dict[str, Any]]:
    return None


def welcome_refusal_copy(refusal: dict[str, Any], *, model: str = "", in_chat: bool = True, door: bool = True) -> str:
    return ""


def welcome_route_refusal(status: Any, message: Any, base_url: Any = None) -> Optional[str]:
    return None


def welcome_route_refusal_copy(kind: str, *, in_chat: bool = True, door: bool = True) -> str:
    return ""


def note_model_switch(agent: Any, headers: Any) -> Optional[str]:
    return None


def apply_model_switch(agent: Any) -> Optional[str]:
    return None


def guest_notice_pending() -> bool:
    return False


def mark_guest_notice_shown() -> bool:
    return False


def set_guest_flag(flag: str) -> Optional[dict[str, Any]]:
    return None


def _save_guest_state(auth_store: dict[str, Any], state: dict[str, Any], source_path: Any) -> None:
    return None


def _account_state_from_token(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise _retired_err()


def settle_after_upgrade(account_state: dict[str, Any]) -> dict[str, Any]:
    """Post-sign-in settle — nothing to settle without a guest to replace."""
    return {"model": "", "changed": False}


def _poll_for_token(*args, **kwargs) -> dict[str, Any]:
    """Keep the device-flow seam live at call time."""
    from thor_cli.auth_device_flow import _poll_for_token as poll
    return poll(*args, **kwargs)


def persist_nous_credentials(*args, **kwargs):
    """Legacy seam: persist ThorHub credentials instead (the Nous OAuth store is gone)."""
    from thor_cli.auth_thorhub import persist_thorhub_credentials as persist
    return persist(*args, **kwargs)


# Public sign-in imports remain here for existing callers and module-attribute patches.
# The flow imports this module only inside calls, so either module can be imported first.
from thor_cli.anon_sign_in import (
    AlreadySignedIn,
    Cancelled,
    Code,
    Completed,
    FREE_TIER_RATE_LIMIT_CARD,
    FREE_TIER_RATE_LIMIT_CHAT,
    Failed,
    LOGIN_BUSY_ELSEWHERE,
    LOGIN_COMMAND,
    LOGIN_DM_ONLY,
    LOGIN_NOT_ALLOWED,
    LOGIN_STARTING,
    SignInState,
    TimedOut,
    UPGRADE_ALREADY_SIGNED_IN,
    UPGRADE_CANCELLED,
    UPGRADE_DO_NOT_SHARE,
    UPGRADE_NOT_COMPLETED,
    UPGRADE_NO_DEFAULT_CHAT,
    UPGRADE_NO_DEFAULT_TERMINAL,
    UPGRADE_START,
    UPGRADE_TIMED_OUT,
    UPGRADE_WAITING,
    UPGRADE_WAITING_UP_TO,
    Waiting,
    _default_persist_guard,
    format_wait_line,
    run_sign_in,
)
from thor_cli.anon_sign_in_cli import (
    drain_sign_in_copy,
    render_sign_in_cli,
    render_sign_in_cli_code,
    upgrade_guest,
)
