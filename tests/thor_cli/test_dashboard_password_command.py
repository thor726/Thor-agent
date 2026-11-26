"""``thor dashboard password``: set the dashboard sign-in without the TTY prompt ``thor dashboard`` offers.

The command writes what that prompt writes (``dashboard.basic_auth``: username, an scrypt hash, a signing
secret when ``config.yaml`` has none; see ``test_dashboard_auth_prompt.py``), reads the password from
standard input with ``--password-stdin``, never from argv, and never prints or stores it. The same
credentials then sign in on ``thor serve`` and on the gateway's own Webapp listener, each started after
the change; a listener restarted after a change ends the sign-ins made with the old password.
"""
from __future__ import annotations

import argparse
import io
import os
import stat
import sys
import types
from pathlib import Path

import pytest
import thor_yaml as yaml

from plugins.dashboard_auth.basic import _verify_password, hash_password
from thor_cli.dashboard_password import cmd_dashboard_password

pytestmark = pytest.mark.platforms("linux")

USER, PASSWORD = "spike-admin", "throwaway-Pw-7f3a9c"  # invented for this test

PASSWORD_ENV = "THOR_DASHBOARD_BASIC_AUTH_PASSWORD"
USERNAME_ENV = "THOR_DASHBOARD_BASIC_AUTH_USERNAME"


@pytest.fixture
def thor_home(tmp_path, monkeypatch):
    home, user = tmp_path / "state", tmp_path / "user"
    home.mkdir(mode=0o700)
    user.mkdir()
    (home / "config.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    monkeypatch.setenv("THOR_HOME", str(home))
    for name in ("THOR_DASHBOARD_BASIC_AUTH_USERNAME", "THOR_DASHBOARD_BASIC_AUTH_PASSWORD",
                 "THOR_DASHBOARD_BASIC_AUTH_PASSWORD_HASH", "THOR_DASHBOARD_BASIC_AUTH_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("THOR_MANAGED_DIR", raising=False)
    return home


def _feed_stdin(monkeypatch, data: bytes):
    monkeypatch.setattr(sys, "stdin",
                        types.SimpleNamespace(buffer=io.BytesIO(data), isatty=lambda: False))


def _set_password(monkeypatch, password=PASSWORD, username=USER):
    _feed_stdin(monkeypatch, (password + "\n").encode())
    return cmd_dashboard_password(argparse.Namespace(username=username, password_stdin=True))


def _set_password_bytes(monkeypatch, stdin: bytes):
    _feed_stdin(monkeypatch, stdin)
    return cmd_dashboard_password(argparse.Namespace(username=USER, password_stdin=True))


def _basic_auth(home) -> dict:
    return ((yaml.safe_load((home / "config.yaml").read_text()) or {}).get("dashboard") or {}).get("basic_auth") or {}


def _files_holding(home, needle: str) -> list[str]:
    return [str(p) for p in home.rglob("*") if p.is_file() and needle.encode() in p.read_bytes()]


def test_the_password_is_stored_as_a_hash_with_a_signing_secret_and_never_shown(
        thor_home, monkeypatch, capsys):
    result = _set_password(monkeypatch)
    assert result == 0
    section = _basic_auth(thor_home)
    # The keys the interactive prompt stores; the emptied plaintext is not written.
    assert sorted(section) == ["password_hash", "secret", "username"]
    assert section["username"] == USER
    assert _verify_password(PASSWORD, section["password_hash"])
    out = capsys.readouterr().out
    assert PASSWORD not in out
    assert _files_holding(thor_home, PASSWORD) == []
    assert stat.S_IMODE((thor_home / "config.yaml").stat().st_mode) == 0o600
    assert "The gateway is running" not in out  # no gateway in this home
    assert "A gateway or thor dashboard / thor serve started from now on uses it." in out


def test_with_the_secret_in_the_environment_a_secret_is_still_written_like_the_prompt_does(
        thor_home, monkeypatch):
    monkeypatch.setenv("THOR_DASHBOARD_BASIC_AUTH_SECRET", "an-invented-environment-signing-secret-0123456789")
    assert _set_password(monkeypatch) == 0
    assert _basic_auth(thor_home)["secret"]


def test_without_a_terminal_or_password_stdin_nothing_is_written(thor_home, monkeypatch, capsys):
    _feed_stdin(monkeypatch, (PASSWORD + "\n").encode())
    with pytest.raises(SystemExit) as exc:  # _read_password raises: no terminal to ask on
        cmd_dashboard_password(argparse.Namespace(username=USER, password_stdin=False))
    assert exc.value.code == 2
    assert "--password-stdin" in capsys.readouterr().err
    assert _basic_auth(thor_home) == {}


def test_an_empty_password_is_refused(thor_home, monkeypatch, capsys):
    for stdin in (b"\n", b""):
        _feed_stdin(monkeypatch, stdin)
        result = cmd_dashboard_password(argparse.Namespace(username=USER, password_stdin=True))
        assert result == 2
        captured = capsys.readouterr()
        assert "Empty password; nothing was changed" in captured.out + captured.err
    assert _basic_auth(thor_home) == {}


def test_only_the_first_line_counts_and_its_line_ending_is_dropped(thor_home, monkeypatch):
    result = _set_password_bytes(monkeypatch, f"{PASSWORD}\r\nsecond line\n".encode())
    assert result == 0
    assert _verify_password(PASSWORD, _basic_auth(thor_home)["password_hash"])


def test_a_lone_carriage_return_is_part_of_the_password(thor_home, monkeypatch):
    assert _set_password_bytes(monkeypatch, b"throwaway-cr\r") == 0
    assert _verify_password("throwaway-cr\r", _basic_auth(thor_home)["password_hash"])


def test_password_stdin_on_a_terminal_is_refused_before_anything_is_typed(thor_home, monkeypatch, capsys):
    master, slave = os.openpty()
    try:
        text = os.fdopen(slave, "r", closefd=False)
        monkeypatch.setattr(sys, "stdin", text)
        with pytest.raises(SystemExit) as exc:
            cmd_dashboard_password(argparse.Namespace(username=USER, password_stdin=True))
    finally:
        os.close(slave)
        os.close(master)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "run without --password-stdin to type it at a hidden prompt" in captured.out + captured.err
    assert _basic_auth(thor_home) == {}


def test_a_non_ascii_password_is_read_as_utf8(thor_home, monkeypatch):
    password = "thröwaway-Pässwort-✓"
    assert _set_password_bytes(monkeypatch, password.encode("utf-8")) == 0  # no trailing newline either
    assert _verify_password(password, _basic_auth(thor_home)["password_hash"])


@pytest.mark.parametrize("stdin, reason", [(b"x" * 1025 + b"\n", "longer than 1024 bytes"),
                                           (b"x" * 1024 + b"\r", "longer than 1024 bytes"),
                                           (b"\xff\xfe-not-utf8\n", "not UTF-8")],
                         ids=["1025-bytes", "1024-bytes-and-a-lone-cr", "not-utf8"])
def test_an_overlong_or_undecodable_password_is_refused(thor_home, monkeypatch, capsys, stdin, reason):
    with pytest.raises(SystemExit) as exc:
        _set_password_bytes(monkeypatch, stdin)
    assert exc.value.code == 2
    assert reason in capsys.readouterr().err
    assert _basic_auth(thor_home) == {}


def test_a_password_in_dotenv_that_would_override_it_is_removed_and_named(thor_home, monkeypatch, capsys):
    dotenv = thor_home / ".env"
    dotenv.write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=stale-env-value\nOTHER_KEY=kept\n")
    dotenv.chmod(0o600)
    result = _set_password(monkeypatch)
    assert result == 0
    out = capsys.readouterr().out
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in out
    assert "stale-env-value" not in out
    text = dotenv.read_text()
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" not in text and "OTHER_KEY=kept" in text
    assert stat.S_IMODE(dotenv.stat().st_mode) == 0o600
    assert "⚠" not in out  # the .env copy is not the calling environment


def test_a_key_the_administrator_pins_is_refused_before_config_yaml_changes(thor_home, monkeypatch, capsys):
    from thor_cli import managed_scope
    managed = thor_home.parent / "managed"
    managed.mkdir()
    (managed / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=pinned-by-admin\n")
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    before = (thor_home / "config.yaml").read_bytes()
    result = _set_password(monkeypatch)
    assert result == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in out and "nothing was changed" in out
    assert "pinned-by-admin" not in out
    assert (thor_home / "config.yaml").read_bytes() == before


def test_changing_it_keeps_the_signing_secret(thor_home, monkeypatch):
    assert _set_password(monkeypatch) == 0
    first = _basic_auth(thor_home)
    assert _set_password(monkeypatch, "another-throwaway-Pw") == 0
    second = _basic_auth(thor_home)
    assert second["secret"] == first["secret"]
    assert second["password_hash"] != first["password_hash"]


def test_password_rotation_preserves_the_username_from_this_homes_dotenv(thor_home, monkeypatch):
    assert _set_password(monkeypatch) == 0
    (thor_home / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_USERNAME=local-operator\n")
    _feed_stdin(monkeypatch, b"new-test-input\n")
    result = cmd_dashboard_password(argparse.Namespace(username=None, password_stdin=True))
    assert result == 0
    assert _basic_auth(thor_home)["username"] == "local-operator"
    assert _verify_password("new-test-input", _basic_auth(thor_home)["password_hash"])
    assert "THOR_DASHBOARD_BASIC_AUTH_USERNAME" not in (thor_home / ".env").read_text()


@pytest.mark.parametrize("name", ["THOR_DASHBOARD_BASIC_AUTH_USERNAME", "'THOR_DASHBOARD_BASIC_AUTH_USERNAME'"])
@pytest.mark.parametrize("template", ["${THOR_DASHBOARD_BASIC_AUTH_USERNAME}",
                                      "${env:THOR_DASHBOARD_BASIC_AUTH_USERNAME}"])
def test_a_username_template_on_an_override_it_removes_is_refused_before_any_write(
        thor_home, monkeypatch, capsys, template, name):
    """The quoted name is the same variable to python-dotenv (the loader) and is removed the same way."""
    (thor_home / "config.yaml").write_text(
        yaml.safe_dump({"dashboard": {"basic_auth": {"username": template}}}), encoding="utf-8")
    (thor_home / ".env").write_text(f"{name}=local-operator\n")
    config_before, dotenv_before = (thor_home / "config.yaml").read_bytes(), (thor_home / ".env").read_bytes()
    _feed_stdin(monkeypatch, b"new-test-input\n")
    result = cmd_dashboard_password(argparse.Namespace(username=None, password_stdin=True))
    assert result == 1
    assert "Set dashboard.basic_auth.username to a literal first" in capsys.readouterr().err
    assert (thor_home / "config.yaml").read_bytes() == config_before
    assert (thor_home / ".env").read_bytes() == dotenv_before


def test_a_named_profile_gets_its_own_sign_in(tmp_path, monkeypatch, capsys):
    user = tmp_path / "user"
    user.mkdir()
    default_root = user / ".thor"
    profile = default_root / "profiles" / "work"
    profile.mkdir(parents=True)
    for root in (default_root, profile):
        (root / "config.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: user)
    monkeypatch.setenv("THOR_HOME", str(profile))
    for name in ("THOR_DASHBOARD_BASIC_AUTH_USERNAME", "THOR_DASHBOARD_BASIC_AUTH_PASSWORD",
                 "THOR_DASHBOARD_BASIC_AUTH_PASSWORD_HASH", "THOR_DASHBOARD_BASIC_AUTH_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("THOR_MANAGED_DIR", raising=False)
    result = _set_password(monkeypatch)
    assert result == 0
    out = capsys.readouterr().out
    assert _verify_password(PASSWORD, _basic_auth(profile)["password_hash"])
    assert _basic_auth(default_root) == {}
    assert "This is profile 'work''s own sign-in" in out
    assert "set those with thor -p default dashboard password." in out  # the shared listeners'


def test_an_override_in_the_checkouts_dotenv_is_named_and_refused(tmp_path):
    """The CLI and ``gateway.run`` both load ``<checkout>/.env`` after the home's, so a sign-in key there
    comes back on every restart. Checked in-process against a real file: the shared checkout's own
    ``.env`` would leak into every other test the runner starts."""
    from thor_cli.dashboard_password import _checkout_refusal
    project_env = tmp_path / ".env"
    assert _checkout_refusal(project_env) is None  # absent
    project_env.write_text("OTHER_KEY=x\nTHOR_DASHBOARD_BASIC_AUTH_USERNAME=\n")
    assert _checkout_refusal(project_env) is None  # empty values override nothing
    project_env.write_text("export THOR_DASHBOARD_BASIC_AUTH_PASSWORD='throwaway-checkout-pw'\n")
    refusal = _checkout_refusal(project_env)
    assert refusal is not None
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in refusal and str(project_env) in refusal
    assert "throwaway-checkout-pw" not in refusal
    assert project_env.read_text().count("throwaway-checkout-pw") == 1  # never edited


def test_a_checkout_override_counts_only_when_the_loader_would_supply_it(tmp_path, monkeypatch):
    """``${VAR}`` in the checkout's ``.env`` is expanded like ``load_thor_dotenv`` does, against the
    environment as it is after the cleanup; an empty result overrides nothing."""
    from thor_cli.dashboard_password import _checkout_refusal
    monkeypatch.delenv("PR4_UNSET_REF", raising=False)
    project_env = tmp_path / ".env"
    project_env.write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=${PR4_UNSET_REF}\n")
    assert _checkout_refusal(project_env) is None
    monkeypatch.setenv("PR4_SET_REF", "throwaway-expanded")
    project_env.write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=${PR4_SET_REF}\n")
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in (_checkout_refusal(project_env) or "")


def test_a_checkout_override_follows_the_loaders_precedence(tmp_path, monkeypatch):
    """With the home's own ``.env`` present the checkout layer only fills gaps, so a value the calling
    environment already sets (warned about separately) wins over it; without one the checkout layer
    overrides that value too. A key in the home's ``.env`` the cleanup removes is no gap-filler."""
    from thor_cli.dashboard_password import _checkout_refusal
    home = tmp_path / "home"
    home.mkdir()
    project_env = tmp_path / ".env"
    project_env.write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=throwaway-checkout-pw\n")
    monkeypatch.setenv("THOR_DASHBOARD_BASIC_AUTH_PASSWORD", "throwaway-inherited")
    assert _checkout_refusal(project_env, home) is not None  # no home .env: the checkout overrides
    (home / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=throwaway-home\n")
    assert _checkout_refusal(project_env, home) is None  # fills gaps only; the inherited value is there
    monkeypatch.delenv("THOR_DASHBOARD_BASIC_AUTH_PASSWORD")
    assert _checkout_refusal(project_env, home) is not None  # the home copy is removed, so a gap


def _managed_dir(tmp_path, basic_auth: dict):
    managed = tmp_path / "managed"
    managed.mkdir()
    (managed / "config.yaml").write_text(yaml.safe_dump({"dashboard": {"basic_auth": basic_auth}}))
    return managed


def test_a_password_hash_the_administrator_pins_is_refused_before_anything_is_written(
        thor_home, monkeypatch, capsys):
    from thor_cli import managed_scope
    managed = _managed_dir(thor_home.parent, {"username": USER, "password_hash": hash_password("throwaway-admin-pinned")})
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    before = (thor_home / "config.yaml").read_bytes()
    result = _set_password(monkeypatch)
    assert result == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "dashboard.basic_auth.password_hash is managed by your administrator" in out
    assert "nothing was changed" in out and "scrypt$" not in out
    assert (thor_home / "config.yaml").read_bytes() == before


def test_a_pinned_username_refuses_another_name_and_keeps_its_own(thor_home, monkeypatch, capsys):
    from thor_cli import managed_scope
    managed = _managed_dir(thor_home.parent, {"username": "pinned-operator"})
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    renamed = _set_password(monkeypatch)  # --username spike-admin
    assert renamed == 1
    assert "dashboard.basic_auth.username is managed by your administrator" in capsys.readouterr().err
    assert _basic_auth(thor_home) == {}
    _feed_stdin(monkeypatch, (PASSWORD + "\n").encode())
    kept = cmd_dashboard_password(argparse.Namespace(username=None, password_stdin=True))
    assert kept == 0
    out = capsys.readouterr().out
    assert "user 'pinned-operator'" in out
    assert _verify_password(PASSWORD, _basic_auth(thor_home)["password_hash"])


def test_a_managed_username_template_is_compared_by_its_effective_value(thor_home, monkeypatch, capsys):
    from thor_cli import managed_scope
    (thor_home / ".env").write_text("PR4_TEST_LOGIN=throwaway-login\n")
    # A real run loads the home's .env into the process env first, so ${...} expands against it.
    monkeypatch.setenv("PR4_TEST_LOGIN", "throwaway-login")
    managed = _managed_dir(thor_home.parent, {"username": "${PR4_TEST_LOGIN}"})
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    _feed_stdin(monkeypatch, (PASSWORD + "\n").encode())
    result = cmd_dashboard_password(argparse.Namespace(username=None, password_stdin=True))
    assert result == 0
    out = capsys.readouterr().out
    assert "user 'throwaway-login'" in out
    assert _verify_password(PASSWORD, _basic_auth(thor_home)["password_hash"])


def test_a_managed_username_template_on_an_override_it_removes_is_refused(thor_home, monkeypatch, capsys):
    from thor_cli import managed_scope
    (thor_home / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_USERNAME=throwaway-login\n")
    managed = _managed_dir(thor_home.parent, {"username": "${THOR_DASHBOARD_BASIC_AUTH_USERNAME}"})
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    before = (thor_home / ".env").read_bytes()
    _feed_stdin(monkeypatch, (PASSWORD + "\n").encode())
    result = cmd_dashboard_password(argparse.Namespace(username=None, password_stdin=True))
    assert result == 1
    assert "references an override this command removes" in capsys.readouterr().err
    assert (thor_home / ".env").read_bytes() == before and _basic_auth(thor_home) == {}


def test_a_password_the_calling_environment_also_sets_is_named_and_still_wins(
        thor_home, monkeypatch, capsys):
    (thor_home / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=throwaway-dotenv-pw\n")
    monkeypatch.setenv("THOR_DASHBOARD_BASIC_AUTH_PASSWORD", "throwaway-inherited-pw")
    result = _set_password(monkeypatch)
    assert result == 0
    out = capsys.readouterr().out
    assert "⚠ THOR_DASHBOARD_BASIC_AUTH_PASSWORD is set in the environment this command runs in" in out
    assert "throwaway-inherited-pw" not in out and "throwaway-dotenv-pw" not in out
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" not in (thor_home / ".env").read_text()


def test_the_restart_hint_names_the_gateway_running_for_this_home(thor_home, monkeypatch, capsys):
    """A gateway owned by this home is a restart hint naming the restart command for its home."""
    from thor_cli.gateway_runtime import GatewayDiscovery, GatewayEndpoint
    endpoint = GatewayEndpoint(profile_id="x", instance_id="y", authority_epoch=1, runtime_protocol=1,
                               api_origin="http://127.0.0.1:9119", supervisor="none", capabilities=frozenset(),
                               control_home=str(thor_home))
    monkeypatch.setattr("thor_cli.gateway_runtime.discover_gateway_endpoint",
                        lambda home, timeout=2.0: GatewayDiscovery(state="ready", endpoint=endpoint))
    assert _set_password(monkeypatch) == 0
    out = capsys.readouterr().out
    assert "The gateway is running: restart it to use the new sign-in (thor -p default gateway restart)." in out


def test_a_profile_password_never_claims_the_shared_gateway_that_serves_the_profile(
        thor_home, monkeypatch, capsys):
    """Dashboard sign-in belongs to the listener's launch home: a gateway serving several profiles signs
    in with its own home's credentials, so a profile's password must not send the user to restart it."""
    from thor_cli.gateway_runtime import GatewayDiscovery, GatewayEndpoint
    other_home = thor_home.parent / "other-home"
    endpoint = GatewayEndpoint(profile_id="x", instance_id="y", authority_epoch=1, runtime_protocol=1,
                               api_origin="http://127.0.0.1:9119", supervisor="none", capabilities=frozenset(),
                               control_home=str(other_home))
    monkeypatch.setattr("thor_cli.gateway_runtime.discover_gateway_endpoint",
                        lambda home, timeout=2.0: GatewayDiscovery(state="ready", endpoint=endpoint))
    assert _set_password(monkeypatch) == 0
    out = capsys.readouterr().out
    assert "restart it to use the new sign-in" not in out
    assert f"serves this profile from {other_home}" in out


def test_dashboard_password_subcommand_parses_and_dispatches(monkeypatch):
    """``thor dashboard password`` reaches cmd_dashboard_password; the bare ``dashboard`` server
    flags are untouched."""
    import thor_cli.dashboard_password as dp
    from thor_cli.subcommands.dashboard import build_dashboard_parser
    parser = argparse.ArgumentParser(prog="thor")
    top = parser.add_subparsers(dest="command")
    seen = []
    build_dashboard_parser(top, cmd_dashboard=lambda args: seen.append(("dashboard", args)),
                           cmd_dashboard_register=lambda args: seen.append(("register", args)))
    args = parser.parse_args(["dashboard", "password", "--username", USER, "--password-stdin"])
    assert args.dashboard_subcommand == "password"
    assert args.username == USER and args.password_stdin is True
    monkeypatch.setattr(dp, "cmd_dashboard_password", lambda a: seen.append(("password", a)) or 7)
    with pytest.raises(SystemExit) as exc:
        args.func(args)
    assert exc.value.code == 7
    assert seen == [("password", args)]
    bare = parser.parse_args(["dashboard", "--port", "9120"])
    assert bare.dashboard_subcommand is None and bare.port == 9120
    bare.func(bare)
    assert seen == [("password", args), ("dashboard", bare)]
