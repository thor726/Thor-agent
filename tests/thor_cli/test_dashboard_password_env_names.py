"""``thor dashboard password`` looks an override up in a ``.env`` by its exact name. On Linux and macOS a
``thor_dashboard_basic_auth_password`` line is another variable, which the provider never reads, so it
stays where it is and nothing is refused for it. On Windows environment names ignore case, so the same line
is THOR_DASHBOARD_BASIC_AUTH_PASSWORD there and would override the new password: the command refuses,
before writing anything, and names the file, line and key as spelled (never the value) so it can be fixed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import sys
import types
from pathlib import Path

import pytest
import thor_yaml as yaml

from plugins.dashboard_auth.basic import _verify_password
from thor_cli.dashboard_password import cmd_dashboard_password

PASSWORD_ENV = "THOR_DASHBOARD_BASIC_AUTH_PASSWORD"
USERNAME_ENV = "THOR_DASHBOARD_BASIC_AUTH_USERNAME"


def _lower_case_home(tmp_path):
    """This home's ``.env`` with lower-case override lines, as ``THOR_HOME`` (set by the test fixtures)."""
    from thor_constants import get_thor_home
    home = get_thor_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("thor_dashboard_basic_auth_password=throwaway-old\n"
                               "thor_dashboard_basic_auth_username=throwaway-env-user\nOTHER_KEY=kept\n")
    project_env = tmp_path / "checkout.env"
    project_env.write_text("thor_dashboard_basic_auth_password=throwaway-checkout\n")
    return home, project_env


@pytest.mark.platforms("posix")
def test_on_posix_a_lower_case_name_is_another_variable_and_stays(tmp_path):
    from thor_cli.dashboard_password import _checkout_refusal, _clear_dotenv_shadows, _current_username
    home, project_env = _lower_case_home(tmp_path)
    before = (home / ".env").read_text()
    assert _current_username() == ""
    assert _checkout_refusal(project_env, home) is None
    assert _clear_dotenv_shadows() == ([], [])
    assert (home / ".env").read_text() == before


def test_a_quoted_key_at_home_does_not_hide_the_checkouts_override(tmp_path):
    """The loader reads ``'KEY'=v`` as KEY, but this home's cleanup (exact names) does not remove that line,
    so the checkout's own KEY only fills a gap that is not there: still refused, as it always was."""
    from thor_cli.dashboard_password import _checkout_refusal
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text(f"'{PASSWORD_ENV}'=throwaway-old\n")
    project_env = tmp_path / "checkout.env"
    project_env.write_text(f"{PASSWORD_ENV}=throwaway-checkout\n")
    refusal = _checkout_refusal(project_env, home)
    assert refusal is not None and PASSWORD_ENV in refusal and "throwaway" not in refusal


def _env_files(tmp_path, home_text: str, checkout_text: str = "OTHER_KEY=x\n"):
    home_env_file, checkout_env = tmp_path / "home.env", tmp_path / "checkout.env"
    home_env_file.write_text(home_text)
    checkout_env.write_text(checkout_text)
    return home_env_file, checkout_env


@pytest.mark.parametrize("spelled", ["thor_dashboard_basic_auth_password", "Thor_Dashboard_Basic_Auth_Password",
                                     "thor_dashboard_basic_auth_username", "THOR_DASHBOARD_BASIC_AUTH_UserName"])
def test_on_windows_an_override_spelled_in_another_case_is_refused_by_file_line_and_spelling(tmp_path, spelled):
    from thor_cli.dashboard_password import _case_variant_refusal
    home_env_file, checkout_env = _env_files(tmp_path, f"OTHER_KEY=a\n{spelled}=throwaway-secret-value\n")
    refusal = _case_variant_refusal([home_env_file, checkout_env], is_windows=True)
    assert refusal is not None
    assert f"{home_env_file} line 2 ({spelled})" in refusal
    assert spelled.upper() in refusal and "delete or rename" in refusal
    assert "throwaway" not in refusal
    assert str(checkout_env) not in refusal


def test_on_windows_the_checkouts_env_is_checked_too_and_every_line_is_named(tmp_path):
    from thor_cli.dashboard_password import _case_variant_refusal
    home_env_file, checkout_env = _env_files(
        tmp_path, f"{PASSWORD_ENV}=throwaway-a\nthor_dashboard_basic_auth_username=throwaway-b\n",
        "x=1\nexport thor_dashboard_basic_auth_password=throwaway-c\nThor_Dashboard_Basic_Auth_Username=\n")
    refusal = _case_variant_refusal([home_env_file, checkout_env], is_windows=True)
    assert f"{home_env_file} line 2 (thor_dashboard_basic_auth_username)" in refusal
    assert (f"{checkout_env} line 2 (thor_dashboard_basic_auth_password), "
            "line 3 (Thor_Dashboard_Basic_Auth_Username)") in refusal
    assert "line 1" not in refusal and "throwaway" not in refusal


@pytest.mark.parametrize("text", [
    f"{PASSWORD_ENV}=throwaway-a\n{USERNAME_ENV}=throwaway-b\n",  # the canonical spelling (cleaned up as before)
    "X_thor_dashboard_basic_auth_password=throwaway\nthor_dashboard_basic_auth_password_old=throwaway\n"
    "# thor_dashboard_basic_auth_password=throwaway\nthor_dashboard_basic_auth_username\n",
])
def test_on_windows_the_canonical_spelling_and_other_names_are_not_refused(tmp_path, text):
    from thor_cli.dashboard_password import _case_variant_refusal
    home_env_file, checkout_env = _env_files(tmp_path, text, text)
    assert _case_variant_refusal([home_env_file, checkout_env, tmp_path / "absent.env"], is_windows=True) is None


def test_on_windows_a_look_alike_line_inside_a_quoted_value_is_refused_too(tmp_path):
    """Lines are read one at a time, as this command reads its ``.env``: a ``p=...`` line inside a quoted
    multi-line value counts. A refusal is safe; renaming or deleting it is the user's call."""
    from thor_cli.dashboard_password import _case_variant_refusal
    home_env_file, checkout_env = _env_files(
        tmp_path, 'NOTE="first\nthor_dashboard_basic_auth_password=text\n"\n')
    assert f"{home_env_file} line 2 (thor_dashboard_basic_auth_password)" in (
        _case_variant_refusal([home_env_file, checkout_env], is_windows=True) or "")


def test_off_windows_the_case_check_does_not_run(tmp_path):
    from thor_cli.dashboard_password import _case_variant_refusal
    home_env_file, checkout_env = _env_files(tmp_path, "thor_dashboard_basic_auth_password=throwaway\n",
                                             "Thor_Dashboard_Basic_Auth_Username=throwaway\n")
    assert _case_variant_refusal([home_env_file, checkout_env], is_windows=False) is None


def _managed_env(tmp_path, monkeypatch, text: str):
    """An administrator-managed ``.env`` holding *text*, found through ``THOR_MANAGED_DIR``."""
    from thor_cli import managed_scope
    managed = tmp_path / "managed"
    managed.mkdir()
    (managed / ".env").write_text(text)
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()
    return managed / ".env"


def test_on_windows_the_administrators_env_is_checked_and_the_line_is_left_to_the_administrator(
        tmp_path, monkeypatch):
    """The managed ``.env`` loads last, with override: a lower-case key there wins on Windows too."""
    from thor_cli.dashboard_password import _case_variant_refusal
    managed_env = _managed_env(tmp_path, monkeypatch, "OTHER_KEY=a\nthor_dashboard_basic_auth_password=throwaway\n")
    home_env_file, checkout_env = _env_files(tmp_path, "OTHER_KEY=x\n")
    refusal = _case_variant_refusal([home_env_file, checkout_env], is_windows=True)
    assert refusal is not None
    assert f"{managed_env} line 2 (thor_dashboard_basic_auth_password)" in refusal
    assert "administrator-managed" in refusal and "an administrator has to" in refusal
    assert PASSWORD_ENV in refusal and "throwaway" not in refusal
    assert str(home_env_file) not in refusal and str(checkout_env) not in refusal


def test_on_windows_the_canonical_spelling_in_the_administrators_env_keeps_its_own_refusal(tmp_path, monkeypatch):
    from thor_cli import managed_scope
    from thor_cli.dashboard_password import _case_variant_refusal, _shadow_refusal
    _managed_env(tmp_path, monkeypatch, f"{PASSWORD_ENV}=throwaway-pinned\n")
    managed_scope.invalidate_managed_cache()
    assert _case_variant_refusal(list(_env_files(tmp_path, "OTHER_KEY=x\n")), is_windows=True) is None
    assert PASSWORD_ENV in (_shadow_refusal() or "")


def test_off_windows_the_administrators_env_is_not_read(tmp_path, monkeypatch):
    from thor_cli.dashboard_password import _case_variant_refusal
    _managed_env(tmp_path, monkeypatch, "thor_dashboard_basic_auth_password=throwaway\n")
    read, real_read = [], Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: read.append(self) or real_read(self))
    assert _case_variant_refusal(list(_env_files(tmp_path, "OTHER_KEY=x\n")), is_windows=False) is None
    assert read == []


def _cli_home(tmp_path, monkeypatch, dotenv: str):
    home, user = tmp_path / "state", tmp_path / "user"
    home.mkdir()
    user.mkdir()
    (home / "config.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (home / ".env").write_text(dotenv)
    monkeypatch.setenv("THOR_HOME", str(home))
    for name in (PASSWORD_ENV, USERNAME_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("THOR_MANAGED_DIR", raising=False)
    return home


def _digests(home) -> dict:
    return {name: hashlib.sha256((home / name).read_bytes()).hexdigest() for name in ("config.yaml", ".env")}


def _basic_auth(home) -> dict:
    return ((yaml.safe_load((home / "config.yaml").read_text()) or {}).get("dashboard") or {}).get("basic_auth") or {}


def _set_password(monkeypatch):
    monkeypatch.setattr(sys, "stdin",
                        types.SimpleNamespace(buffer=io.BytesIO(b"throwaway-new-Pw-1\n"), isatty=lambda: False))
    return cmd_dashboard_password(argparse.Namespace(username="spike-admin", password_stdin=True))


@pytest.mark.platforms("windows")
def test_on_windows_the_command_refuses_a_lower_case_override_and_succeeds_once_it_is_fixed(
        tmp_path, monkeypatch, capsys):
    home = _cli_home(tmp_path, monkeypatch, "OTHER_KEY=kept\nthor_dashboard_basic_auth_password=throwaway-old-Pw\n")
    before = _digests(home)
    result = _set_password(monkeypatch)
    assert result == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert f"{home / '.env'} line 2 (thor_dashboard_basic_auth_password)" in out
    assert "delete or rename" in out and "nothing was changed" in out
    assert "throwaway" not in out
    assert _digests(home) == before
    (home / ".env").write_text("OTHER_KEY=kept\nOLD_thor_dashboard_basic_auth_password=throwaway-old-Pw\n")
    fixed = _set_password(monkeypatch)
    assert fixed == 0
    captured = capsys.readouterr()
    assert "throwaway" not in captured.out + captured.err
    assert (home / ".env").read_text() == "OTHER_KEY=kept\nOLD_thor_dashboard_basic_auth_password=throwaway-old-Pw\n"


@pytest.mark.platforms("windows")
def test_on_windows_the_command_refuses_a_lower_case_override_in_the_administrators_env(
        tmp_path, monkeypatch, capsys):
    home = _cli_home(tmp_path, monkeypatch, "OTHER_KEY=kept\n")
    managed = tmp_path / "managed"
    managed.mkdir()
    (managed / ".env").write_text("thor_dashboard_basic_auth_password=throwaway-admin-Pw\n")
    monkeypatch.setenv("THOR_MANAGED_DIR", str(managed))
    before = _digests(home)
    result = _set_password(monkeypatch)
    assert result == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert f"{managed / '.env'} line 1 (thor_dashboard_basic_auth_password)" in out
    assert "an administrator has to" in out and "throwaway" not in out
    assert _digests(home) == before


@pytest.mark.platforms("posix")
def test_on_posix_the_command_leaves_a_lower_case_line_alone_and_sets_the_password(tmp_path, monkeypatch, capsys):
    dotenv = "OTHER_KEY=kept\nthor_dashboard_basic_auth_password=throwaway-old-Pw\n"
    home = _cli_home(tmp_path, monkeypatch, dotenv)
    result = _set_password(monkeypatch)
    assert result == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "line 2" not in out and "throwaway" not in out
    assert (home / ".env").read_text() == dotenv
    assert _verify_password("throwaway-new-Pw-1", _basic_auth(home)["password_hash"])
