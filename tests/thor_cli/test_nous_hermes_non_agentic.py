"""Tests for the Nous-Thor-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"thor"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``thor-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "thor" tag namespace.

``is_nous_thor_non_agentic`` should only match the actual Nous Research
Thor-3 / Thor-4 chat family.
"""

from __future__ import annotations

import pytest

from thor_cli.model_switch import (
    _THOR_MODEL_WARNING,
    _check_thor_model_warning,
    is_nous_thor_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "Thor Labs/Thor-3-Llama-3.1-70B",
        "Thor Labs/Thor-3-Llama-3.1-405B",
        "thor-3",
        "Thor-3",
        "thor-4",
        "thor-4-405b",
        "thor_4_70b",
        "openrouter/thor3:70b",
        "openrouter/thorlabs/thor-4-405b",
        "Thor Labs/Thor3",
        "thor-3.1",
    ],
)
def test_matches_real_nous_thor_chat_models(model_name: str) -> None:
    assert is_nous_thor_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Thor 3/4"
    )
    assert _check_thor_model_warning(model_name) == _THOR_MODEL_WARNING


