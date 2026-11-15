"""A sed -i of Thor's own config.yaml is gated whichever way the shell spells THOR_HOME (#144033).

The home fold knew only the absolute native path. On Windows the default home is
``%LOCALAPPDATA%\\thor``, and the agent's Git Bash terminal writes that file as
``/c/Users/<me>/AppData/Local/thor/config.yaml``, ``~/AppData/Local/thor/config.yaml``,
``$HOME/AppData/Local/thor/config.yaml`` or ``$LOCALAPPDATA/thor/config.yaml``. Every one of
those passed as safe, so an in-place edit there rewrote the approval policy (approvals.mode, yolo,
allowlist) mid-session. Platform-independent: the spellings are folded from the resolved home, and a
custom THOR_HOME under the user home reproduces the same gap on any OS.
"""

import pytest

from tools import approval_home_fold
from tools.approval import detect_dangerous_command

_PROFILE = r"C:\Users\tester"


def _is_dangerous(cmd: str) -> bool:
    return bool(detect_dangerous_command(cmd)[0])


@pytest.fixture
def windows_default_home(monkeypatch):
    """The Windows default THOR_HOME, reached through the profile the way Git Bash spells it."""
    monkeypatch.setenv("HOME", _PROFILE)
    monkeypatch.setenv("USERPROFILE", _PROFILE)
    monkeypatch.setenv("LOCALAPPDATA", _PROFILE + r"\AppData\Local")
    monkeypatch.setenv("THOR_HOME", _PROFILE + r"\AppData\Local\thor")


class TestSpellingsOfTheThorHome:
    def test_the_native_and_forward_slash_forms_were_always_gated(self, windows_default_home):
        assert _is_dangerous("sed -i s/a/b/ ~/.thor/config.yaml") is True
        assert _is_dangerous("sed -i s/a/b/ C:/Users/tester/AppData/Local/thor/config.yaml") is True

    @pytest.mark.parametrize("target", [
        "/c/Users/tester/AppData/Local/thor/config.yaml",  # Git Bash drive form
        "/C/Users/tester/AppData/Local/thor/config.yaml",
        "~/AppData/Local/thor/config.yaml",  # home-relative
        "$HOME/AppData/Local/thor/config.yaml",
        "${HOME}/AppData/Local/thor/config.yaml",
        "$LOCALAPPDATA/thor/config.yaml",  # the variable the default is built from
        "${LOCALAPPDATA}/thor/config.yaml",
        "${USERPROFILE}/AppData/Local/thor/config.yaml",
        r"%LOCALAPPDATA%\thor\config.yaml",
    ])
    def test_every_spelling_of_the_windows_default_home_is_gated(self, windows_default_home, target):
        assert _is_dangerous(f"sed -i s/a/b/ {target}") is True

    def test_the_thor_env_file_is_gated_too(self, windows_default_home):
        assert _is_dangerous("sed -i s/a/b/ /c/Users/tester/AppData/Local/thor/.env") is True
        assert _is_dangerous("sed -i s/a/b/ $LOCALAPPDATA/thor/.env") is True

    def test_the_long_in_place_flag_and_perl_are_gated(self, windows_default_home):
        assert _is_dangerous("sed --in-place s/a/b/ ~/AppData/Local/thor/config.yaml") is True
        assert _is_dangerous("perl -pi -e s/a/b/ ${HOME}/AppData/Local/thor/config.yaml") is True

    def test_a_custom_home_under_the_user_home_is_gated_on_any_os(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/tester")
        monkeypatch.setenv("THOR_HOME", "/home/tester/thor-data")
        assert _is_dangerous("sed -i s/a/b/ ~/thor-data/config.yaml") is True
        assert _is_dangerous("sed -i s/a/b/ $HOME/thor-data/config.yaml") is True

    @pytest.mark.platforms("windows")
    def test_a_home_spelled_in_another_case_still_folds_on_windows(self, monkeypatch):
        monkeypatch.setenv("HOME", r"c:\users\tester")
        monkeypatch.setenv("THOR_HOME", r"C:\Users\tester\AppData\Local\thor")
        assert _is_dangerous("sed -i s/a/b/ ~/AppData/Local/thor/config.yaml") is True


class TestPathBelowCaseFold:
    """``_path_below`` folds case only on a Windows host, so a HOME and THOR_HOME that differ
    only in case still nest there. Runs on every lane by stubbing the host fact."""

    @pytest.mark.parametrize(("family", "expected"), [("win32", "AppData/Local/thor"), ("linux", None)])
    def test_case_fold_follows_the_host_os_family(self, monkeypatch, family, expected):
        monkeypatch.setattr(approval_home_fold.facts, "os_family", lambda: family)
        assert approval_home_fold._path_below(r"c:\users\tester", r"C:\Users\tester\AppData\Local\thor") == expected


class TestUnrelatedPathsStaySafe:
    """Folding a spelling must not turn a sibling config.yaml into Thor's own policy file."""

    @pytest.mark.parametrize("target", [
        "/c/Users/tester/projects/app/config.yaml",
        "~/projects/app/config.yaml",
        "$LOCALAPPDATA/other/config.yaml",
        "/c/Users/tester/AppData/Local/thor2/config.yaml",
    ])
    def test_a_sibling_config_yaml_is_not_flagged_as_thor_policy(self, windows_default_home, target):
        assert _is_dangerous(f"sed -i s/a/b/ {target}") is False

    def test_a_sibling_of_a_custom_home_is_not_flagged(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/tester")
        monkeypatch.setenv("THOR_HOME", "/home/tester/thor-data")
        assert _is_dangerous("sed -i s/a/b/ ~/thor-data-old/config.yaml") is False
        assert _is_dangerous("sed -i s/a/b/ $HOME/thor-data-old/config.yaml") is False
