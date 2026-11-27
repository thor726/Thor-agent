"""Vendor-agnostic Gemini model-family rules live in one shared module (agent/gemini_model_family.py)
and the URL helpers in agent/gemini_urls.py; the native adapter and the transports re-export/use them
instead of carrying private copies."""

import pytest

from agent.gemini_model_family import (
    GEMINI_DEFAULT_MAX_OUTPUT_TOKENS,
    build_gemini_thinking_config,
    effective_gemini_max_output_tokens,
    gemini_sampling_deprecated,
    gemini_uses_thinking_level,
    gemini_version,
    normalize_gemini_thinking_config,
    snake_case_gemini_thinking_config,
)
from agent.gemini_urls import (
    is_gemini_openai_compat_base_url,
    is_native_gemini_base_url,
    is_vertex_express_base_url,
    normalize_gemini_base_url,
)


@pytest.mark.parametrize("model, expected", [
    ("gemini-4-argon", (4, 0)),
    ("google/gemini-3.8-flash", (3, 8)),
    ("gemini-flash-latest", (0, 0)),
    ("gemini-exp-1206", (0, 0)),
    ("gemma-3", (0, 0)),
])
def test_gemini_version(model, expected):
    assert gemini_version(model) == expected


@pytest.mark.parametrize("model, expected", [
    ("gemini-3-flash", True),
    ("gemini-2.5-flash", False),
    ("gemini-flash-latest", True),
    ("gemini-4-argon", True),
])
def test_gemini_uses_thinking_level(model, expected):
    assert gemini_uses_thinking_level(model) is expected


@pytest.mark.parametrize("model, expected", [
    ("gemini-3.6-flash", True),
    ("gemini-4-argon", True),
    ("gemini-3.5-flash", False),
    ("gemini-2.5-flash", False),
])
def test_gemini_sampling_deprecated(model, expected):
    assert gemini_sampling_deprecated(model) is expected


def test_build_gemini_thinking_config_gemini4_disabled_gets_floor_level_hidden():
    assert build_gemini_thinking_config("gemini-4-argon", {"enabled": False}) == {
        "includeThoughts": False, "thinkingLevel": "low"}


def test_build_gemini_thinking_config_gemini25_disabled_gets_zero_budget():
    assert build_gemini_thinking_config("gemini-2.5-flash", {"enabled": False}) == {
        "includeThoughts": False, "thinkingBudget": 0}


def test_build_gemini_thinking_config_pro_high_effort():
    assert build_gemini_thinking_config("gemini-3-pro", {"effort": "high"}) == {
        "includeThoughts": True, "thinkingLevel": "high"}


def test_build_gemini_thinking_config_rejects_non_gemini():
    assert build_gemini_thinking_config("gemma-3", {"effort": "high"}) is None
    assert build_gemini_thinking_config("gemini-2.5-flash", {"effort": "high"}) == {"includeThoughts": True}


def test_thinking_config_round_trips_to_snake_case():
    assert snake_case_gemini_thinking_config({"includeThoughts": True, "thinkingLevel": "High"}) == {
        "include_thoughts": True, "thinking_level": "high"}
    assert normalize_gemini_thinking_config({"thinking_budget": 100, "include_thoughts": True}) == {
        "thinkingBudget": 100, "includeThoughts": True}


def test_effective_max_output_tokens_raises_cap_only_when_thinking():
    assert effective_gemini_max_output_tokens(None, None) == GEMINI_DEFAULT_MAX_OUTPUT_TOKENS
    assert effective_gemini_max_output_tokens(4096, {"includeThoughts": True, "thinkingLevel": "high"}) == GEMINI_DEFAULT_MAX_OUTPUT_TOKENS
    assert effective_gemini_max_output_tokens(4096, None) == 4096
    # Hidden thoughts never balloon a small caller budget.
    assert effective_gemini_max_output_tokens(64, {"includeThoughts": False, "thinkingLevel": "low"}) == 64


def test_normalize_gemini_base_url_adds_version_and_completes_express():
    assert normalize_gemini_base_url("") == "https://generativelanguage.googleapis.com/v1beta"
    assert normalize_gemini_base_url("https://generativelanguage.googleapis.com") == (
        "https://generativelanguage.googleapis.com/v1beta")
    assert normalize_gemini_base_url("https://generativelanguage.googleapis.com/v1beta/") == (
        "https://generativelanguage.googleapis.com/v1beta")
    assert normalize_gemini_base_url("https://aiplatform.googleapis.com") == (
        "https://aiplatform.googleapis.com/v1beta1/publishers/google")


def test_gemini_base_url_routing():
    assert is_native_gemini_base_url("https://generativelanguage.googleapis.com/v1beta") is True
    assert is_native_gemini_base_url("https://generativelanguage.googleapis.com/v1beta/openai") is False
    assert is_vertex_express_base_url("https://aiplatform.googleapis.com/v1beta1/publishers/google") is True
    assert is_vertex_express_base_url("https://aiplatform.googleapis.com/v1/endpoints/openapi") is False
    assert is_gemini_openai_compat_base_url("https://generativelanguage.googleapis.com/v1beta/openai") is True
    assert is_gemini_openai_compat_base_url("https://generativelanguage.googleapis.com/v1beta") is False


def test_reasoning_effort_xhigh_lift_applies_to_hydrogen_and_neon():
    from agent.reasoning_effort import gemini_thinking_config

    assert gemini_thinking_config("gemini-4-hydrogen", {"effort": "max"}) == {
        "includeThoughts": True, "thinkingLevel": "xhigh"}
    assert gemini_thinking_config("gemini-4-neon", {"effort": "ultra"}) == {
        "includeThoughts": True, "thinkingLevel": "xhigh"}
    # Argon answers 400 to xhigh: the shared mapping stops at high.
    assert gemini_thinking_config("gemini-4-argon", {"effort": "max"}) == {
        "includeThoughts": True, "thinkingLevel": "high"}
