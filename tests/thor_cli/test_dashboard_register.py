"""Tests for ``thor dashboard register`` — retired with the Thor Portal.

Registering a self-hosted dashboard OAuth client only existed on the Nous Portal.
ThorHub has no OAuth clients (static API keys only), so the command fails honestly
instead of posting to a dead host.
"""

from __future__ import annotations

import argparse

import pytest

import thor_cli.dashboard_register as dr


def test_dashboard_register_is_retired(capsys):
    with pytest.raises(SystemExit) as exc:
        dr.cmd_dashboard_register(argparse.Namespace(name=None, redirect_uri=None, portal_url=None))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "retired" in out
    assert "ThorHub" in out
    assert "thor auth add thor" in out
