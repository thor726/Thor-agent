"""Browser challenges for the anonymous free tier — RETIRED with the Nous Portal (Fase 4 debrand).

The free tier's proof-of-work / browser-check flow (``anon_challenge``) only ever ran against the
Nous Portal's anonymous surface. ThorHub has no free tier and no challenges, so nothing is ever
pending: the public names are kept so the TUI free-tier RPCs and the agent's error paths keep
resolving, and every action is a no-op or an honest error.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

from thor_cli.auth_constants import AuthError

BROWSER_CAPABILITY = "browser-v1"
CHALLENGE_EVENT = "free_tier.challenge"
CHALLENGE_WAIT_SECONDS = 120.0
CHALLENGE_COPY = "Thor needs to run a quick check before starting your free session."

T = TypeVar("T")


@dataclass(frozen=True)
class BrowserChallenge:
    """Kept for import compatibility; never constructed anymore."""

    url: str = ""
    attempt: int = 0

    def as_payload(self) -> dict[str, Any]:
        return {"url": self.url, "attempt": self.attempt}


class AnonChallengeRequired(AuthError):
    """Kept for import compatibility; never raised anymore (no free tier to challenge for)."""

    def __init__(self, challenge: BrowserChallenge, *, portal_base_url: str = "", anon_token: str = "",
                 **kwargs: Any) -> None:
        super().__init__("The guest free tier is retired — ThorHub has no free tier.",
                         provider="thor", code="thorhub_no_free_tier")
        self.challenge = challenge


def signin_required_error(message: Any = None) -> AuthError:
    return AuthError(str(message or "The guest free tier is retired — ThorHub has no free tier."),
                     provider="thor", code="thorhub_no_free_tier", relogin_required=False)


def server_message(value: Any) -> str:
    return str(value or "")


def client_surface() -> str:
    return ""


def client_info() -> dict[str, Any]:
    return {}


def user_agent() -> str:
    from thor_cli.version_info import thor_user_agent
    return thor_user_agent()


def parse_browser_challenge(payload: dict[str, Any], portal_base_url: str) -> Optional[BrowserChallenge]:
    return None


def challenge_error(payload: dict[str, Any], *, portal_base_url: str, anon_token: str,
                    **kwargs: Any) -> AuthError:
    return signin_required_error()


@contextlib.contextmanager
def background_caller():
    """No-op context manager (the proxy no longer announces a free-tier challenge)."""
    yield


def pending_challenge() -> Optional[dict[str, Any]]:
    return None


def record_host_outcome(url: str, attempt: int, outcome: str) -> bool:
    return False


def reset_for_tests() -> None:
    return None


def present(challenge: BrowserChallenge) -> None:
    return None


def wait_for_challenge(exc: AnonChallengeRequired) -> bool:
    return False


def run_with_challenge(exchange: Callable[[], T]) -> T:
    return exchange()
