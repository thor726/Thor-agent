"""Tests for the Hermes 3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
the family tag anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``hermes-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under that tag namespace.

``is_thor_thor_non_agentic`` should only match the actual Nous Research
Hermes-3 / Hermes-4 chat family. The ``NousResearch/Hermes-…`` prefixes are
real third-party model IDs on OpenRouter/Together, kept verbatim so the
detector matches what providers actually serve.
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
