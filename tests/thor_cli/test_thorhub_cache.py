"""Tests for the ThorHub prompt-cache display in /topup (Fase 6).

The cache summary (hit rate + saved quota) is computed server-side by
ThorHub (llm-gateway) and arrives inside the ``cache`` block of
``GET /portal/member/me``. The agent only renders it: full block -> cache
lines in the balance view; missing/malformed block -> plain balance view,
never a crash. No Nous, no portal.thor-agent.local, no dollar credits.
"""

from __future__ import annotations

import pytest

from agent.thorhub_usage import build_credits_view
from thor_cli.thorhub_account import (
    format_thorhub_balance_lines,
    format_thorhub_cache_lines,
)


_BALANCE = {
    "user_name": "Tes",
    "token_limit": 1_000_000,
    "tokens_used": 36_908,
    "tokens_remaining": 963_092,
    "key_days_left": 24,
}

_CACHE = {
    "cached_tokens": 8_000,
    "cache_creation_tokens": 2_000,
    "requests": 10,
    "requests_with_cache": 7,
    "cache_hit_rate": 42.5,
    "tokens_saved": 7_200,
}


def test_cache_lines_full_block():
    lines = format_thorhub_cache_lines(_CACHE)
    assert any("42.5% hit" in line for line in lines)
    assert any("8.000 token dari cache" in line for line in lines)
    assert any("Hemat kuota: 7.200 token" in line for line in lines)
    assert any("7 dari 10" in line for line in lines)


def test_cache_lines_absent_or_malformed_is_empty():
    assert format_thorhub_cache_lines(None) == ()
    assert format_thorhub_cache_lines({}) == ()
    assert format_thorhub_cache_lines("bukan-dict") == ()
    # Block present but with no usable field -> no lines, no crash.
    assert format_thorhub_cache_lines({"cache_hit_rate": "n/a"}) == ()


def test_cache_lines_zero_saved_omits_savings_line():
    lines = format_thorhub_cache_lines({**_CACHE, "tokens_saved": 0})
    assert not any("Hemat kuota" in line for line in lines)
    assert any("42.5% hit" in line for line in lines)


def test_balance_lines_include_cache_when_gateway_sends_it():
    lines = format_thorhub_balance_lines({**_BALANCE, "cache": _CACHE})
    assert any("Terpakai: 36.908 / 1.000.000 token" in line for line in lines)
    assert any("Prompt-cache ThorHub" in line for line in lines)
    assert any("Hemat kuota: 7.200 token" in line for line in lines)


def test_balance_lines_without_cache_are_unchanged():
    lines = format_thorhub_balance_lines(_BALANCE)
    assert any("Terpakai: 36.908 / 1.000.000 token" in line for line in lines)
    assert not any("Prompt-cache" in line for line in lines)
    assert not any("Hemat kuota" in line for line in lines)


@pytest.fixture
def _stub_balance(monkeypatch):
    def _install(data):
        monkeypatch.setattr("thor_cli.thorhub_account.fetch_thorhub_balance", lambda: data)

    return _install


def test_credits_view_shows_cache_savings(_stub_balance):
    _stub_balance({**_BALANCE, "cache": _CACHE})
    view = build_credits_view()
    assert view.logged_in is True
    assert any("Hemat kuota: 7.200 token" in line for line in view.balance_lines)
    assert any("42.5% hit" in line for line in view.balance_lines)


def test_credits_view_without_cache_still_works(_stub_balance):
    _stub_balance(_BALANCE)
    view = build_credits_view()
    assert view.logged_in is True
    assert view.balance_lines
    assert not any("Prompt-cache" in line for line in view.balance_lines)
