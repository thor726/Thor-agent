"""The one Thor sign-in: the plain device-code login every surface renders, plus its states and copy."""

from __future__ import annotations

import contextlib
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, ContextManager, Iterator, Optional

from thor_cli.auth_constants import httpx


UPGRADE_START = "Sign in with a Thor account to unlock more models and tools."
UPGRADE_ALREADY_SIGNED_IN = "Already signed in."
UPGRADE_DO_NOT_SHARE = "Do not share this code."
UPGRADE_TIMED_OUT = "That sign-in link has expired. Start again whenever you're ready."
UPGRADE_NOT_COMPLETED = "Sign-in didn't finish. Try again whenever you're ready."
# The account service was busy or unreachable mid sign-in (an ``anon_*`` code from
# ``anon_auth.classify_mint_exception``): nothing was saved, so the copy reassures before the way forward.
UPGRADE_SERVICE_BUSY = ("Signing in couldn't finish because the Thor service is busy. "
                        "Try again in {wait}. Your session is still here in the meantime.")
UPGRADE_SERVICE_UNREACHABLE = ("The Thor service couldn't be reached to finish signing you in. "
                               "Check your internet connection and try again. Your session is still here.")

UPGRADE_NO_DEFAULT_TERMINAL = "No default model is set yet; run `thor model` to pick one."
UPGRADE_NO_DEFAULT_CHAT = "No default model is set yet; run /model to pick one."
UPGRADE_WAITING = "Waiting for sign-in..."
UPGRADE_WAITING_UP_TO = "Waiting for sign-in, up to {minutes}."
UPGRADE_CANCELLED = "\nSign-in cancelled."
LOGIN_COMMAND = "/login"
LOGIN_STARTING = "Starting sign-in..."
LOGIN_DM_ONLY = "Sign in from a direct message with Thor."
LOGIN_BUSY_ELSEWHERE = "Another sign-in is already running on this Thor. Try again in a few minutes."
LOGIN_NOT_ALLOWED = "Only an operator of this Thor can sign it in."
# The card form (a surface with its own sign-in button) and the chat form (names /login).
FREE_TIER_RATE_LIMIT_CARD = (
    "You've used up the allowance for chatting without signing in. It refreshes in {reset}. "
    "Sign in for a bigger allowance, it's free.")
FREE_TIER_RATE_LIMIT_CHAT = FREE_TIER_RATE_LIMIT_CARD + " To sign in: /login."


def format_wait_line(expires_in: int) -> str:
    """The honest "up to N minutes" line; N = ceil(expires_in / 60), singular at 1."""
    n = max(1, math.ceil(max(0, int(expires_in)) / 60))
    return UPGRADE_WAITING_UP_TO.format(minutes=f"{n} minute" if n == 1 else f"{n} minutes")


# --- Sign-in states -----------------------------------------------------------------------------
#
# One sign-in composition (:func:`run_sign_in`) yields these; every surface is a renderer over them.
# Each state carries its own user copy, so no renderer ever maps a reason to a string: ``.copy`` is
# the in-chat form (never a raw exception, a URL or a ``thor`` verb) and ``.copy_terminal`` the
# form a top-level terminal command prints.


@dataclass(frozen=True)
class SignInState:
    """One step of a sign-in. Every state carries its own user copy; renderers never map."""

    kind: ClassVar[str] = ""
    terminal: ClassVar[bool] = True     # False only for Code and Waiting
    ok: ClassVar[bool] = False          # exit-code 0 / "this ended well"
    precondition: ClassVar[bool] = False  # True only for AlreadySignedIn

    @property
    def copy(self) -> str:
        """The in-chat form."""
        return ""

    @property
    def copy_terminal(self) -> str:
        """The terminal form; differs for Completed and Failed."""
        return self.copy


@dataclass(frozen=True)
class Code(SignInState):
    """The device page link and the sign-in code, plus the clock the caller may show."""

    link: str
    code: str
    expires_in: int
    interval: int
    kind: ClassVar[str] = "code"
    terminal: ClassVar[bool] = False

    @property
    def copy(self) -> str:
        return UPGRADE_DO_NOT_SHARE

    @property
    def copy_with_wait(self) -> str:
        """The do-not-share line plus the honest "up to N minutes"; composed here, never in a renderer."""
        return f"{UPGRADE_DO_NOT_SHARE} {format_wait_line(self.expires_in)}"


@dataclass(frozen=True)
class Waiting(SignInState):
    kind: ClassVar[str] = "waiting"
    terminal: ClassVar[bool] = False

    @property
    def copy(self) -> str:
        return UPGRADE_WAITING


@dataclass(frozen=True)
class Completed(SignInState):
    """``handoff`` holds the guest handoff's result lines (what moved, what to reconnect), empty
    when the sign-in replaced no free tier. ``handoff_status`` is the latest handoff record it ran,
    in ``guest_handoff.wire_status`` form, for a surface that renders the result itself."""

    email: str = ""
    model: str = ""
    model_changed: bool = False
    handoff: tuple[str, ...] = ()
    handoff_status: Optional[dict[str, Any]] = None
    kind: ClassVar[str] = "completed"
    ok: ClassVar[bool] = True

    def _lines(self, no_default: str) -> str:
        lines = [f"Signed in as {self.email}." if self.email else "Signed in.", *self.handoff]
        if self.model_changed:
            lines.append(f"Default model is now {self.model}." if self.model else no_default)
        return "\n".join(lines)

    @property
    def copy(self) -> str:
        return self._lines(UPGRADE_NO_DEFAULT_CHAT)

    @property
    def copy_terminal(self) -> str:
        return self._lines(UPGRADE_NO_DEFAULT_TERMINAL)


@dataclass(frozen=True)
class Cancelled(SignInState):
    """Stopped from outside before anything was saved: the user's cancel, a newer /login, a shutdown."""

    kind: ClassVar[str] = "cancelled"

    @property
    def copy(self) -> str:
        return UPGRADE_CANCELLED.strip()


@dataclass(frozen=True)
class TimedOut(SignInState):
    #: The enriched device-auth guidance, for a surface with room for it. Never shown in a chat.
    detail: str = ""
    kind: ClassVar[str] = "timed_out"

    @property
    def copy(self) -> str:
        return UPGRADE_TIMED_OUT


@dataclass(frozen=True)
class Failed(SignInState):
    """``reason``: an ``anon_*`` code naming the service's verdict (busy, unreachable...), or "" for
    anything unnamed. ``retry_after``: the wait the service asked for, in seconds (0 when it named
    none). ``retryable``: whether a later attempt can succeed, so a renderer knows to offer "try
    again" and when."""

    reason: str = ""
    detail: str = ""
    retry_after: float = 0.0
    kind: ClassVar[str] = "failed"

    @property
    def retryable(self) -> bool:
        from thor_cli import anon_auth as _core
        return bool(self.reason.startswith("anon_") and self.reason not in _core.ANON_TERMINAL_CODES)

    @property
    def copy(self) -> str:
        from thor_cli import anon_auth as _core
        if self.reason in _core.ANON_UNREACHABLE_CODES:
            return UPGRADE_SERVICE_UNREACHABLE
        if self.reason in (_core.ANON_RATE_LIMITED, _core.ANON_GATE_PAUSED):
            return UPGRADE_SERVICE_BUSY.format(wait=_core.friendly_wait(self.retry_after or 60))
        if self.reason in _core.ANON_FAILURE_COPY:
            return _core.anon_failure_copy(self.reason, retry_after=self.retry_after)
        return UPGRADE_NOT_COMPLETED

    @property
    def copy_terminal(self) -> str:
        if self.reason and self.copy != UPGRADE_NOT_COMPLETED:
            return self.copy
        return f"Sign-in failed: {self.detail}" if self.detail else UPGRADE_NOT_COMPLETED


@dataclass(frozen=True)
class AlreadySignedIn(SignInState):
    kind: ClassVar[str] = "already_signed_in"
    ok: ClassVar[bool] = True
    precondition: ClassVar[bool] = True

    @property
    def copy(self) -> str:
        return UPGRADE_ALREADY_SIGNED_IN


def _failed_from_exception(exc: BaseException) -> Failed:
    """A ``Failed`` that keeps the service's own verdict: the ``anon_*`` code and wait hint an
    ``AuthError`` carries, or the wire's shape for a transport error. The raw detail never reaches a
    chat; ``copy_terminal`` may show it when nothing better is known."""
    from thor_cli import anon_auth as _core
    err = _core.classify_mint_exception(exc)
    reason = str(err.code or "")
    if reason == _core.ANON_SERVER_ERROR and not isinstance(exc, _core.AuthError):
        # An unnamed local failure (a bad CA bundle, a lock timeout): keep the generic copy and its
        # terminal detail rather than blaming the service.
        return Failed(reason="", detail=str(exc))
    return Failed(reason=reason, detail=str(exc), retry_after=float(err.retry_after or 0.0))


def _default_persist_guard(is_cancelled: Callable[[], bool]) -> Callable[[], ContextManager[bool]]:
    """The persist guard used when a surface brings none: proceed unless the attempt was stopped."""
    @contextlib.contextmanager
    def _guard():
        yield not is_cancelled()
    return _guard


def run_sign_in(
    *,
    timeout_seconds: float = 15.0,
    cancelled: Optional[Callable[[], bool]] = None,
    replace_account: bool = False,
    persist_guard: Optional[Callable[[], ContextManager[bool]]] = None,
    scope: Optional[Callable[[], ContextManager[Any]]] = None,
    client_factory: Optional[Callable[[float, Any], ContextManager[Any]]] = None,
) -> Iterator[SignInState]:
    """Sign in with a Thor account — RETIRED with the Thor Portal (Fase 4 debrand).

    The Portal's device-code login is gone, so there is no sign-in to run: an install that already
    has a ThorHub key yields :class:`AlreadySignedIn`, anything else yields one terminal
    :class:`Failed` telling the user to add a ThorHub key. The generator contract (exactly one
    terminal state, never a raise out of ``next()``) is preserved.
    """
    from thor_cli.thorhub_account import thorhub_api_key

    if thorhub_api_key() and not replace_account:
        yield AlreadySignedIn()
        return
    yield Failed(
        reason="thorhub_no_free_tier",
        detail="Thor Portal sign-in is retired — add a ThorHub key with `thor auth add thor` "
               "or set THORHUB_API_KEY.")
