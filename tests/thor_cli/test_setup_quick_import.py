"""First-time Quick Setup after an agent import: a model the import brought is kept by default
instead of being replaced by the ThorHub step."""

from argparse import Namespace
from unittest.mock import patch

import pytest


def _fake_import(_thor_home):
    """What an agent import leaves behind: a model in config.yaml and its key in .env."""
    from thor_cli.config import load_config, save_config, save_env_value
    config = load_config()
    config["model"] = {"provider": "openrouter", "default": "anthropic/claude-sonnet-4.5"}
    save_config(config)
    save_env_value("OPENROUTER_API_KEY", "test-openrouter-key")
    return "OpenClaw"


@pytest.mark.parametrize("switch", [False, True])
def test_quick_setup_keeps_imported_model(switch):
    """The imported model survives Quick Setup either way: keeping it skips the ThorHub
    guidance step, and switching to it only shows the guidance — the ThorHub step never
    writes a model itself (the user picks their own provider/model/key in ``thor setup``)."""
    from thor_cli.config import get_env_value, load_config
    from thor_cli.setup import run_setup_wizard

    questions = []

    def answer(question, choices, default=0, description=None):
        # Enter on every menu (the mode menu's default is Quick Setup), except the keep/switch
        # question when the test switches.
        questions.append(question)
        if switch and "switch to ThorHub" in question:
            return 1
        return default

    with patch("thor_cli.setup.is_interactive_stdin", return_value=True), \
            patch("thor_cli.setup.offer_agent_import", side_effect=_fake_import), \
            patch("thor_cli.setup.prompt_choice", side_effect=answer), \
            patch("thor_cli.setup.setup_terminal_backend"), \
            patch("thor_cli.setup.setup_gateway") as gateway, \
            patch("thor_cli.setup._print_setup_summary"), \
            patch("thor_cli.setup._record_setup_completed"):
        run_setup_wizard(Namespace(non_interactive=False, section=None, reset=False,
                                   reconfigure=False, quick=False))

    model = load_config()["model"]
    assert {k: model.get(k) for k in ("provider", "default")} == {
        "provider": "openrouter", "default": "anthropic/claude-sonnet-4.5"}
    assert get_env_value("OPENROUTER_API_KEY") == "test-openrouter-key"
    gateway.assert_called_once()  # the rest of Quick Setup still runs
    assert any("Keep your imported model (OpenRouter · anthropic/claude-sonnet-4.5)" in q
               for q in questions), questions
