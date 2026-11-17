"""Tests for banner toolset name normalization and skin color usage."""

from unittest.mock import patch

from rich.console import Console

from thor_cli import banner
import model_tools
import tools.mcp_tool_discovery

def test_cprint_falls_back_to_plain_print_when_prompt_toolkit_has_no_console(capsys):
    with patch(
        "prompt_toolkit.print_formatted_text",
        side_effect=RuntimeError("no console screen buffer"),
    ):
        banner.cprint("fallback text")

    assert capsys.readouterr().out == "fallback text\n"

def test_baked_banner_uses_live_identity(monkeypatch):
    from thor_cli import banner, version_info

    monkeypatch.setattr(version_info, "get_code_identity", lambda: {"short_sha": "a1b2c3d4"})
    assert banner._baked_banner_state() == {"upstream": "a1b2c3d4", "local": "a1b2c3d4", "ahead": 0}
