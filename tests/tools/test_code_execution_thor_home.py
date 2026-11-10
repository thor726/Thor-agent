"""execute_code child env honors the multiplexed per-turn THOR_HOME override (#110303).

Under a multiplexed Desktop/Dashboard connection one server process serves several
profiles, binding a context-local THOR_HOME override per turn. ``_build_child_env``
scrubs the server process's ``os.environ`` — which carries the machine-default
THOR_HOME — so without the rewrite below, skill scripts run via ``execute_code``
silently read/write the wrong profile's directory.
"""

import sys

import pytest

from thor_constants import (
    get_thor_home_override,
    reset_thor_home_override,
    set_thor_home_override,
)
from tools.code_execution_env import _build_child_env


@pytest.fixture
def home_override():
    tokens = []

    def _set(path):
        tokens.append(set_thor_home_override(path))
        return str(path)

    yield _set
    for token in reversed(tokens):
        reset_thor_home_override(token)


def _child_env():
    return _build_child_env(
        rpc_endpoint="sock",
        rpc_token="tok",
        tmpdir="/tmp/thor-test",
        child_python=sys.executable,
    )


class TestMultiplexedThorHome:
    def test_override_rewrites_stale_server_default_per_turn(self, monkeypatch, home_override, tmp_path):
        """The reported bug: a child must see the ACTIVE profile's home, not the server default,
        and sequential turns for different profiles each see their own."""
        monkeypatch.setenv("THOR_HOME", "/machine/default/.thor")
        alpha = home_override(tmp_path / "profiles" / "alpha")
        assert _child_env()["THOR_HOME"] == alpha
        beta = home_override(tmp_path / "profiles" / "beta")
        assert _child_env()["THOR_HOME"] == beta

    def test_no_override_leaves_inherited_value_untouched(self, monkeypatch):
        """Dedicated per-profile processes (no override): zero behavior change."""
        assert get_thor_home_override() is None
        monkeypatch.setenv("THOR_HOME", "/machine/default/.thor")

        assert _child_env()["THOR_HOME"] == "/machine/default/.thor"
