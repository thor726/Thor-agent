"""Tests for the chat-only (non-agentic) model warning detector.

The detector matches real third-party chat-only model IDs that providers
actually serve (kept verbatim in the fixtures below for that reason — they
are external model names, not this product's identity). A bare substring
check false-positived on unrelated local Modelfiles such as
``hermes-brain:qwen3-14b-ctx16k``, a tool-capable Qwen3 wrapper under a
similar tag namespace, so the match must stay narrowly anchored.
"""

from __future__ import annotations

import pytest

from thor_cli.model_switch import (
    _THOR_MODEL_WARNING,
    _check_thor_model_warning,
    is_thor_thor_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Hermes-3-Llama-3.1-70B",
        "NousResearch/Hermes-3-Llama-3.1-405B",
        "hermes-3",
        "Hermes-3",
        "hermes-4",
        "hermes-4-405b",
        "hermes_4_70b",
        "openrouter/hermes3:70b",
        "openrouter/nousresearch/hermes-4-405b",
        "NousResearch/Hermes3",
        "hermes-3.1",
    ],
)
def test_matches_real_hermes_chat_models(model_name: str) -> None:
    assert is_thor_thor_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as a Hermes 3/4 chat model"
    )
    assert _check_thor_model_warning(model_name) == _THOR_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        "hermes-brain:qwen3-14b-ctx16k",  # local Modelfile, tool-capable
        "qwen3:14b",
        "claude-opus-4-6",
        "gpt-5.2",
        "deepseek-chat",
    ],
)
def test_does_not_match_agentic_or_unrelated_models(model_name: str) -> None:
    assert not is_thor_thor_non_agentic(model_name)
    assert _check_thor_model_warning(model_name) == ""
