"""Regression tests: libXi repair belongs to install, not verify (mirrors libatomic)."""

from pathlib import Path

import pytest

from pm.packages import CuaDriver


_LOADER = (
    "cua-driver: error while loading shared libraries: libXi.so.6: "
    "cannot open shared object file: No such file or directory"
)


def _driver_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.platforms("posix")
def test_staged_repair_installs_libxi_then_reprobes(tmp_path, monkeypatch):
    driver = tmp_path / "cua-driver"
    _driver_script(driver, f'#!/bin/sh\necho "{_LOADER}" >&2\nexit 127\n')
    monkeypatch.setattr("pm.packages.current_target", lambda: "linux-x64")

    calls = {"n": 0}

    def install():
        calls["n"] += 1
        _driver_script(driver, "#!/bin/sh\necho cua-driver-rs 0.6.1\n")
        return True, "install with sudo apt-get install -y libxi6"

    monkeypatch.setattr("pm.libxi.try_install_libxi", install)
    package = CuaDriver()
    first = package.verify(tmp_path, "linux-x64")
    assert "libXi.so.6" in first

    repaired = package.repair_staged_verification(tmp_path, "linux-x64", first)

    assert calls["n"] == 1
    assert repaired == ("", "")


@pytest.mark.platforms("posix")
def test_staged_repair_ignores_other_reasons(tmp_path, monkeypatch):
    """A non-libXi failure (bad download, other missing libs) must not touch apt."""
    monkeypatch.setattr("pm.packages.current_target", lambda: "linux-x64")
    calls = {"n": 0}

    def install():
        calls["n"] += 1
        return True, "should not run"

    monkeypatch.setattr("pm.libxi.try_install_libxi", install)
    package = CuaDriver()
    reason = "cua-driver --version exited 1: some unrelated corruption"
    repaired = package.repair_staged_verification(tmp_path, "linux-x64", reason)

    assert calls["n"] == 0
    assert repaired == (reason, "")


def test_libxi_auto_repair_never_reads_a_tty(monkeypatch):
    from pm import libxi

    monkeypatch.setattr(libxi, "_ATTEMPT", None)
    monkeypatch.setattr(libxi, "_is_root", lambda: False)
    monkeypatch.setattr(libxi, "_host_install_command", lambda: ("apt-get", "install", "-y", "libxi6"))
    monkeypatch.setattr(libxi.shutil, "which", lambda name: "/usr/bin/sudo" if name == "sudo" else None)

    captured = {}

    def run(argv, **kwargs):
        captured["argv"] = argv
        captured.update(kwargs)
        return type("Result", (), {"returncode": 1})()

    monkeypatch.setattr(libxi.subprocess, "run", run)

    attempted, _remedy = libxi.try_install_libxi()

    assert attempted is False
    assert captured["argv"][:2] == ["/usr/bin/sudo", "-n"]
    assert captured["stdin"] is libxi.subprocess.DEVNULL


def test_libxi_attempt_is_once_per_process(monkeypatch):
    from pm import libxi

    monkeypatch.setattr(libxi, "_ATTEMPT", None)
    calls = {"n": 0}

    def attempt():
        calls["n"] += 1
        return (False, "remedy")

    monkeypatch.setattr(libxi, "_attempt", attempt)
    assert libxi.try_install_libxi() == (False, "remedy")
    assert libxi.try_install_libxi() == (False, "remedy")
    assert calls["n"] == 1


def test_libxi_distro_package_map():
    from pm import libxi

    # Every installer entry installs the distro's real libXi package name.
    assert libxi._INSTALLERS["apt-get"] == ("apt-get", "install", "-y", "libxi6")
    assert libxi._INSTALLERS["dnf"] == ("dnf", "install", "-y", "libXi")
    # Debian-family detection prefers apt-get.
    assert libxi._manager_order({"ubuntu", "generic"}) == ("apt-get",)
    assert libxi._manager_order({"rhel"}) == ("dnf", "yum")
