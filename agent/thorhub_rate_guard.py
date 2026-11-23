"""Cross-session rate limit guard for ThorHub.

Writes rate limit state to a shared file so all sessions (CLI, gateway, cron,
auxiliary) can check whether ThorHub is currently rate-limited before making
requests. Without it each 429 fans out into up to 9 calls per turn (3 SDK
retries x 3 Thor retries), all counted against the key quota.

ThorHub has no free/welcome tier: a 429 is an ordinary key rate limit, and
there is no anonymous allowance to split by.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from typing import Any, Mapping, Optional
from utils import atomic_write_text
from agent.retry_utils import parse_retry_after_seconds
from agent.rate_limit_tracker import (
    _BUCKET_TAGS, _fmt_seconds, _safe_float, _safe_int, has_rate_limit_headers, lower_headers,
)

logger = logging.getLogger(__name__)

# Reset windows shorter than this are transient upstream jitter, not a quota
# exhaustion worth a cross-session breaker trip.
_MIN_RESET_FOR_BREAKER_SECONDS = 60.0

format_remaining = _fmt_seconds


def _state_path() -> str:
    """Path to the ThorHub rate limit state file."""
    try:
        from thor_constants import get_thor_home
        base = get_thor_home()
    except ImportError:
        base = os.path.join(os.path.expanduser("~"), ".thor")
    return os.path.join(base, "rate_limits", "thorhub.json")


def _parse_reset_seconds(headers: Optional[Mapping[str, str]]) -> Optional[float]:
    """Best reset estimate (seconds from now) from hourly, per-minute, then retry-after headers."""
    lowered = lower_headers(headers)
    for key in ("x-ratelimit-reset-requests-1h", "x-ratelimit-reset-requests"):
        val = _safe_float(lowered.get(key), 0.0)
        if val > 0:
            return val
    retry_after = parse_retry_after_seconds(lowered.get("retry-after"))
    return retry_after if retry_after else None


def record_thorhub_rate_limit(
    *, headers: Optional[Mapping[str, str]] = None, error_context: Optional[dict[str, Any]] = None,
    default_cooldown: float = 300.0,
) -> None:
    """Record that ThorHub is rate-limited in the shared state file.

    Reset time comes from ``error_context["reset_at"]`` (the 429 body's own wait), then headers, then
    ``default_cooldown``. The body wins: a refusal says when to retry, while the
    hourly bucket's reset header is that window's end even with requests left in it.
    """
    now = time.time()
    reset_at = None
    if isinstance(error_context, dict):
        ctx_reset = error_context.get("reset_at")
        if isinstance(ctx_reset, (int, float)) and ctx_reset > now:
            reset_at = float(ctx_reset)
    if reset_at is None and (header_seconds := _parse_reset_seconds(headers)) is not None:
        reset_at = now + header_seconds
    if reset_at is None:
        reset_at = now + default_cooldown

    state = {"reset_at": reset_at, "recorded_at": now, "reset_seconds": reset_at - now}
    try:
        atomic_write_text(_state_path(), json.dumps(state))
        logger.info("ThorHub rate limit recorded: resets in %.0fs (at %.0f)", reset_at - now, reset_at)
    except Exception as exc:
        logger.debug("Failed to write ThorHub rate limit state: %s", exc)


def thorhub_rate_limit_remaining() -> Optional[float]:
    """Seconds remaining until reset, or None if not rate-limited (expired state is removed)."""
    path = _state_path()
    try:
        with open(path, encoding="utf-8-sig") as f:
            state = json.load(f)
        remaining = state.get("reset_at", 0) - time.time()
        if remaining > 0:
            return remaining
        with contextlib.suppress(OSError):
            os.unlink(path)
        return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        return None


def clear_thorhub_rate_limit() -> None:
    """Clear the rate limit state (e.g., after a successful ThorHub request)."""
    try:
        os.unlink(_state_path())
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.debug("Failed to clear ThorHub rate limit state: %s", exc)


def _is_exhausted(remaining: Optional[int], reset: Optional[float]) -> bool:
    """remaining == 0 AND a reset window long enough to be a real quota exhaustion."""
    return (
        remaining is not None
        and remaining <= 0
        and reset is not None
        and reset >= _MIN_RESET_FOR_BREAKER_SECONDS
    )


def is_genuine_thorhub_rate_limit(
    *, headers: Optional[Mapping[str, str]] = None, last_known_state: Optional[Any] = None,
) -> bool:
    """Decide whether a 429 from ThorHub is a real key rate limit.

    ThorHub multiplexes upstream providers behind one key, so a 429 may be one
    upstream model out of capacity (clears in seconds) rather than our quota;
    tripping the breaker on that would block every ThorHub model for minutes.
    Only an exhausted bucket (remaining == 0 with reset >= 60s) in the 429's
    own headers, or in the last-known-good ``RateLimitState``, is genuine.
    """
    if _has_exhausted_bucket(_parse_buckets_from_headers(headers)):
        return True
    return last_known_state is not None and _has_exhausted_bucket_in_object(last_known_state)


def _parse_buckets_from_headers(
    headers: Optional[Mapping[str, str]],
) -> dict[str, tuple[Optional[int], Optional[float]]]:
    """(remaining, reset_seconds) per bucket from x-ratelimit-* headers ({} if none)."""
    lowered = lower_headers(headers)
    if not has_rate_limit_headers(lowered):
        return {}
    result: dict[str, tuple[Optional[int], Optional[float]]] = {}
    for _attr, tag in _BUCKET_TAGS:
        remaining = _safe_int(lowered.get(f"x-ratelimit-remaining-{tag}"), None)
        reset = _safe_float(lowered.get(f"x-ratelimit-reset-{tag}"), None)
        if remaining is not None or reset is not None:
            result[tag] = (remaining, reset)
    return result


def _has_exhausted_bucket(buckets: Mapping[str, tuple[Optional[int], Optional[float]]]) -> bool:
    return any(_is_exhausted(remaining, reset) for remaining, reset in buckets.values())


def _has_exhausted_bucket_in_object(state: Any) -> bool:
    """Check a RateLimitState-like object (duck-typed; missing attrs are skipped)."""
    for attr, _tag in _BUCKET_TAGS:
        bucket = getattr(state, attr, None)
        if bucket is None or (getattr(bucket, "limit", 0) or 0) <= 0:
            continue
        remaining = getattr(bucket, "remaining", 0) or 0
        reset = getattr(bucket, "remaining_seconds_now", None)
        if reset is None:
            reset = getattr(bucket, "reset_seconds", 0.0) or 0.0
        if _is_exhausted(remaining, reset):
            return True
    return False
