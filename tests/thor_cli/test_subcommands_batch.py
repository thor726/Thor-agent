"""Smoke tests for the batch-extracted subcommand parser builders.

Each ``build_<group>_parser`` should attach its subcommand to a subparsers
group and wire ``func`` to the injected handler. These are intentionally
light — the byte-identical ``--help`` verification done at extraction time is
the real behavioral guarantee; this just guards against a module failing to
import or a builder raising.
"""

from __future__ import annotations

import argparse


from thor_cli.subcommands.config import build_config_parser



def _h(name):
    def handler(args):  # pragma: no cover - identity only
        return name
    handler.__name__ = f"cmd_{name}"
    return handler






def test_config_get_unset_subcommands_parse():
    """`thor config get/unset` parse key args (and --json for get)."""
    parser = argparse.ArgumentParser(prog="thor")
    sub = parser.add_subparsers(dest="command")
    handler = _h("config")
    build_config_parser(sub, cmd_config=handler)

    ns = parser.parse_args(["config", "get", "terminal.backend", "--json"])
    assert ns.func is handler
    assert ns.config_command == "get"
    assert ns.key == "terminal.backend"
    assert ns.json is True

    ns = parser.parse_args(["config", "unset", "terminal.backend"])
    assert ns.func is handler
    assert ns.config_command == "unset"
    assert ns.key == "terminal.backend"




# ── removed commands: `thor login` / `thor portal` ────
#
# Both were removed with the Nous Portal retirement (nous-removal Fase 1):
# `thor login` was a deprecated stub and `thor portal` was the Portal
# entry point. The parser must reject them as unknown subcommands and must
# not advertise them in `thor --help`.


def test_removed_login_and_portal_subcommands_are_rejected():
    """`thor login` / `thor portal` parse as invalid choices (exit 2)."""
    import pytest

    from thor_cli.main import _build_cli_parser

    parser, _subparsers = _build_cli_parser()
    for argv in (["login"], ["login", "--provider", "thor"], ["portal"], ["portal", "info"]):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(argv)
        assert exc.value.code == 2


def test_removed_login_and_portal_absent_from_help():
    """Neither removed subcommand appears in `thor --help`."""
    from thor_cli.main import _build_cli_parser

    parser, _subparsers = _build_cli_parser()
    help_text = parser.format_help()
    assert "\n  portal " not in help_text
    assert "\n  login " not in help_text
