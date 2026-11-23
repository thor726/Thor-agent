"""Tests for agent/thorhub_rate_guard.py — cross-session ThorHub rate limit guard."""

import json
import os
import time

import pytest


@pytest.fixture
def rate_guard_env(tmp_path, monkeypatch):
    """Isolate rate guard state to a temp directory."""
    thor_home = str(tmp_path / ".thor")
    os.makedirs(thor_home, exist_ok=True)
    monkeypatch.setenv("THOR_HOME", thor_home)
    # Clear any cached module-level imports
    return thor_home


class TestRecordThorhubRateLimit:
    """Test recording rate limit state."""

    def test_records_with_header_reset(self, rate_guard_env):
        from agent.thorhub_rate_guard import record_thorhub_rate_limit, _state_path

        headers = {"x-ratelimit-reset-requests-1h": "1800"}
        record_thorhub_rate_limit(headers=headers)

        path = _state_path()
        assert os.path.exists(path)
        with open(path, encoding="utf-8-sig") as f:
            state = json.load(f)
        assert state["reset_seconds"] == pytest.approx(1800, abs=2)
        assert state["reset_at"] > time.time()




    def test_falls_back_to_error_context_reset_at(self, rate_guard_env):
        from agent.thorhub_rate_guard import record_thorhub_rate_limit, _state_path

        future_reset = time.time() + 900
        record_thorhub_rate_limit(
            headers=None,
            error_context={"reset_at": future_reset},
        )

        with open(_state_path(), encoding="utf-8-sig") as f:
            state = json.load(f)
        assert state["reset_at"] == pytest.approx(future_reset, abs=1)


    def test_the_429_bodys_wait_outranks_the_hourly_window_end(self, rate_guard_env):
        # A 429 body said retry after 410 s; the hourly bucket's reset header (its
        # window end, ~1 h) turned that into an hour-long block on the next turns.
        from agent.thorhub_rate_guard import record_thorhub_rate_limit, _state_path

        record_thorhub_rate_limit(
            headers={"x-ratelimit-remaining-requests-1h": "37", "x-ratelimit-reset-requests-1h": "3594"},
            error_context={"reset_at": time.time() + 410},
        )

        with open(_state_path(), encoding="utf-8-sig") as f:
            state = json.load(f)
        assert state["reset_seconds"] == pytest.approx(410, abs=2)

    def test_custom_default_cooldown(self, rate_guard_env):
        from agent.thorhub_rate_guard import record_thorhub_rate_limit, _state_path

        record_thorhub_rate_limit(headers=None, default_cooldown=120.0)

        with open(_state_path(), encoding="utf-8-sig") as f:
            state = json.load(f)
        assert state["reset_seconds"] == pytest.approx(120, abs=2)



class TestThorhubRateLimitRemaining:
    """Test checking remaining rate limit time."""


    def test_returns_remaining_seconds_when_active(self, rate_guard_env):
        from agent.thorhub_rate_guard import record_thorhub_rate_limit, thorhub_rate_limit_remaining

        record_thorhub_rate_limit(headers={"x-ratelimit-reset-requests-1h": "600"})
        remaining = thorhub_rate_limit_remaining()
        assert remaining is not None
        assert 595 < remaining <= 605  # ~600 seconds, allowing for test execution time

    def test_returns_none_when_expired(self, rate_guard_env):
        from agent.thorhub_rate_guard import thorhub_rate_limit_remaining, _state_path

        # Write an already-expired state
        path = _state_path()
        state_dir = os.path.dirname(path)
        os.makedirs(state_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"reset_at": time.time() - 10, "recorded_at": time.time() - 100}, f)

        assert thorhub_rate_limit_remaining() is None
        # File should be cleaned up
        assert not os.path.exists(_state_path())



class TestClearThorhubRateLimit:
    """Test clearing rate limit state."""

    def test_clears_existing_file(self, rate_guard_env):
        from agent.thorhub_rate_guard import (
            record_thorhub_rate_limit,
            clear_thorhub_rate_limit,
            thorhub_rate_limit_remaining,
            _state_path,
        )

        record_thorhub_rate_limit(headers={"retry-after": "600"})
        assert thorhub_rate_limit_remaining() is not None

        clear_thorhub_rate_limit()
        assert thorhub_rate_limit_remaining() is None
        assert not os.path.exists(_state_path())








class TestParseResetSeconds:
    """Test header parsing for reset times."""

    def test_case_insensitive_headers(self, rate_guard_env):
        from agent.thorhub_rate_guard import _parse_reset_seconds

        headers = {"X-Ratelimit-Reset-Requests-1h": "1200"}
        assert _parse_reset_seconds(headers) == 1200.0

    def test_returns_none_for_empty_headers(self):
        from agent.thorhub_rate_guard import _parse_reset_seconds

        assert _parse_reset_seconds(None) is None
        assert _parse_reset_seconds({}) is None

    def test_ignores_zero_values(self):
        from agent.thorhub_rate_guard import _parse_reset_seconds

        headers = {"x-ratelimit-reset-requests-1h": "0"}
        assert _parse_reset_seconds(headers) is None



class TestAuxiliaryClientIntegration:
    """Test that the auxiliary client respects the rate guard."""

    def test_try_thorhub_skips_when_rate_limited(self, rate_guard_env, monkeypatch):
        from agent.thorhub_rate_guard import record_thorhub_rate_limit

        # Record a rate limit
        record_thorhub_rate_limit(headers={"retry-after": "600"})

        # Mock _read_thorhub_auth to return valid creds (would normally succeed)
        import agent.auxiliary_client as aux
        monkeypatch.setattr(aux, "_read_thorhub_auth", lambda: {
            "api_key": "sk-thor-test",
            "base_url": "https://llm.thormarket.site/v1",
            "source": "pool",
        })

        monkeypatch.setattr(aux, "_resolve_thorhub_runtime_api", lambda **kw: None)
        result = aux._try_thorhub()
        assert result == (None, None)



class TestIsGenuineThorhubRateLimit:
    """Tell a real account-level 429 apart from an upstream-capacity 429.

    ThorHub multiplexes upstreams (DeepSeek, Kimi, MiMo, Thor).
    A 429 from an upstream out of capacity should NOT trip the
    cross-session breaker; a real user-quota 429 should.
    """

    def test_exhausted_hourly_bucket_in_429_headers_is_genuine(self):
        from agent.thorhub_rate_guard import is_genuine_thorhub_rate_limit

        headers = {
            "x-ratelimit-limit-requests-1h": "800",
            "x-ratelimit-remaining-requests-1h": "0",
            "x-ratelimit-reset-requests-1h": "3100",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-remaining-requests": "198",
            "x-ratelimit-reset-requests": "40",
        }
        assert is_genuine_thorhub_rate_limit(headers=headers) is True

    def test_bare_429_with_no_headers_is_upstream(self):
        from agent.thorhub_rate_guard import is_genuine_thorhub_rate_limit

        assert is_genuine_thorhub_rate_limit(headers=None) is False
        assert is_genuine_thorhub_rate_limit(headers={}) is False
        assert is_genuine_thorhub_rate_limit(
            headers={"content-type": "application/json"}
        ) is False



    def test_last_known_state_all_healthy_stays_upstream(self):
        # Prior state was healthy; bare 429 arrives; should be treated
        # as upstream capacity.
        from agent.thorhub_rate_guard import is_genuine_thorhub_rate_limit
        from agent.rate_limit_tracker import parse_rate_limit_headers

        prior_headers = {
            "x-ratelimit-limit-requests-1h": "800",
            "x-ratelimit-remaining-requests-1h": "750",
            "x-ratelimit-reset-requests-1h": "2000",
            "x-ratelimit-limit-requests": "200",
            "x-ratelimit-remaining-requests": "180",
            "x-ratelimit-reset-requests": "30",
            "x-ratelimit-limit-tokens": "800000",
            "x-ratelimit-remaining-tokens": "790000",
            "x-ratelimit-reset-tokens": "30",
            "x-ratelimit-limit-tokens-1h": "8000000",
            "x-ratelimit-remaining-tokens-1h": "7900000",
            "x-ratelimit-reset-tokens-1h": "2000",
        }
        last_state = parse_rate_limit_headers(prior_headers, provider="nous")
        assert is_genuine_thorhub_rate_limit(
            headers=None, last_known_state=last_state
        ) is False



class TestRateGuardStateEncoding:
    """Regression for #18637: the cross-session rate-limit state file was
    opened without ``encoding="utf-8"`` on both the atomic write (os.fdopen)
    and the read. On Windows Chinese locales the platform default decoder
    raises on UTF-8 bytes written by a peer process, silently losing the
    rate-limit guard and re-enabling the retry amplification the module was
    built to prevent.
    """

    def test_read_uses_utf8_under_non_utf8_locale(self, rate_guard_env, monkeypatch):
        import builtins

        from agent.thorhub_rate_guard import thorhub_rate_limit_remaining, _state_path

        path = _state_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # State JSON written with a UTF-8 provider label. Python's json
        # module itself escapes non-ASCII by default, but a peer writer
        # (or human) using ensure_ascii=False produces raw UTF-8 bytes,
        # which is what this guards against.
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f'{{"reset_at": {int(time.time()) + 3600:d}, "provider": "中文", "recorded_at": 0}}'
            )

        real_open = builtins.open

        def guarded_open(file, mode="r", *args, **kwargs):
            try:
                is_target = str(file) == str(path)
            except Exception:
                is_target = False
            # The repo encoding policy makes reads BOM-tolerant, so both
            # UTF-8 family codecs satisfy this regression guard.
            if (
                is_target
                and "b" not in mode
                and kwargs.get("encoding") not in ("utf-8", "utf-8-sig")
            ):
                raise UnicodeDecodeError(
                    "gbk", b"\x94", 0, 1, "illegal multibyte sequence"
                )
            return real_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", guarded_open)

        remaining = thorhub_rate_limit_remaining()
        assert remaining is not None and remaining > 0
