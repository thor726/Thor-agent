"""Regression: the model-switch pipeline must not call an undefined warning helper.

The 2026-11 rebrand commit dropped ``_check_thor_model_warning`` (and the regex it used)
from ``thor_cli/model_switch.py`` while leaving two call sites behind — every model switch
died with ``NameError: name '_check_thor_model_warning' is not defined``. These tests pin both
the symbol's existence and the warning/quiet behaviour so the gap cannot silently return.
"""

import pytest

from thor_cli.model_switch import (
    _check_thor_model_warning,
    is_nous_thor_non_agentic,
)


def test_warning_helper_is_defined_and_callable():
    # The exact failure mode: attribute existed in call sites but not in the module.
    assert callable(_check_thor_model_warning)
    assert callable(is_nous_thor_non_agentic)


@pytest.mark.parametrize("model", [
    "nousresearch/hermes-3-llama-3.1-405b",
    "Nous-Hermes-4-70B",
    "hermes-3",
    "hermes_4",
    "hermes-3.1",
])
def test_non_agentic_models_warn(model):
    assert _check_thor_model_warning(model)


@pytest.mark.parametrize("model", [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "qwen/qwen3-coder",
    "deepseek-chat",          # a real agentic model on several providers
    "some-chat-model",
    "meta-llama/llama-3.1-70b",
    "moonshotai/kimi-k2",
    "google/gemini-2.5-pro",
    "",
])
def test_agentic_and_plain_chat_models_stay_quiet(model):
    assert _check_thor_model_warning(model) == ""


def test_helper_never_raises_on_junk():
    # A cosmetic warning must never be able to abort a model switch.
    assert _check_thor_model_warning("") == ""
    assert _check_thor_model_warning("\x00!!/hermes-9") == ""
    assert _check_thor_model_warning(None) == ""  # type: ignore[arg-type]  # callers pass agent.model


def test_switch_warning_list_builds_without_name_error():
    """Mirrors ``_build_switch_result``'s warnings comprehension verbatim."""
    for validation_message, new_model in (
        (None, "anthropic/claude-sonnet-4"),
        (None, "nousresearch/hermes-3-llama-3.1-405b"),
        ("existing warning", "openai/gpt-4o"),
    ):
        warnings = [w for w in (validation_message, _check_thor_model_warning(new_model)) if w]
        assert isinstance(warnings, list)
