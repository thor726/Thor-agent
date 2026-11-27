"""``SystemHost`` read-only probes for ``thor gateway migrate --backends`` (Fase 2).

Behaviour contracts only: profile argv, systemctl-show parsing, home identity and
gateway ownership — no service is touched, no config is written.
"""

from __future__ import annotations

from pathlib import Path

from thor_cli import gateway_migrate_backends_host as host_mod
from thor_cli.gateway_runtime_service_identity import apply_unset_environment


def test_profile_args_empty_for_a_home_that_is_no_profile(tmp_path):
    assert host_mod.profile_args(tmp_path / "somewhere") == []


def test_profile_args_names_a_named_profile_home(tmp_path):
    assert host_mod.profile_args(tmp_path / "profiles" / "work") == ["-p", "work"]


def test_exec_start_argv_parses_a_systemctl_show_value():
    value = "{ path=/usr/bin/thor ; argv[]=thor dashboard --port 9119 ; ignore_errors=no ;}"
    assert host_mod.exec_start_argv(value) == ["thor", "dashboard", "--port", "9119"]
    assert host_mod.exec_start_argv("no argv here") == []


def test_parse_show_reads_systemctl_key_value_lines():
    assert host_mod.parse_show("MainPID=123\nActiveState=active\nNoEquals\n") == {
        "MainPID": "123", "ActiveState": "active"}


def test_unit_text_environment_reads_systemd_assignments():
    env, problem = host_mod.unit_text_environment(
        "Environment=\"THOR_HOME=/tmp/x\" FOO=bar\n")
    assert (env, problem) == ({"THOR_HOME": "/tmp/x", "FOO": "bar"}, None)


def test_system_host_same_home_matches_only_its_own_home(tmp_path):
    home = tmp_path / "home"
    host = host_mod.SystemHost(home)
    assert host.same_home(str(home)) is True
    assert host.same_home(str(tmp_path / "other")) is False


def test_system_host_gateway_owner_is_own_for_an_unknown_home(tmp_path):
    # A home no profile owns has no other gateway that could serve it; the owner
    # is "own", never a guess, and the probe never raises.
    host = host_mod.SystemHost(tmp_path / "home")
    assert host.gateway_owner() == ("own", None)


def test_system_host_os_family_is_a_known_family(tmp_path):
    assert host_mod.SystemHost(tmp_path / "home").os_family() in {"linux", "darwin", "win32"}


def test_detached_unit_prefix_and_dropin_carry_the_thor_name(tmp_path):
    host = host_mod.SystemHost(tmp_path / "home")
    assert host_mod.DETACHED_UNIT_PREFIX == "thor-backend-migration-"
    assert host.DROPIN_NAME == "thor-migrated.conf"
    assert "thor gateway migrate --backends --restore" in host.DROPIN_TEXT
    assert "RestartPreventExitStatus=78" in host.DROPIN_TEXT


def test_apply_unset_environment_drops_a_bare_name_and_a_matching_assignment():
    env = {"A": "1", "B": "2", "C": "3"}
    assert apply_unset_environment(dict(env), "A B=2") == {"C": "3"}
    # A NAME=VALUE only drops that exact assignment; a different value keeps it.
    assert apply_unset_environment({"B": "2"}, "B=9") == {"B": "2"}
    assert apply_unset_environment({"B": "2"}, "B") == {}
