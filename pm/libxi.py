"""Install the host X11 library package required by the Linux cua-driver binary.

Mirrors pm.libatomic (official Linux Node needs libatomic.so.1): the cua-driver
Computer-Use binary links against libXi.so.6 (X11 input extension) on headless
servers that never installed an X stack. Two entry points:
try_install_libxi() is the non-interactive repair run from
CuaDriver.repair_staged_verification(), and the package map follows the same
distro matrix libatomic uses. Package verification itself remains diagnostic and
side-effect free.
"""

from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess


_INSTALLERS: dict[str, tuple[str, ...]] = {
    "apt-get": ("apt-get", "install", "-y", "libxi6"),
    "dnf": ("dnf", "install", "-y", "libXi"),
    "yum": ("yum", "install", "-y", "libXi"),
    "zypper": ("zypper", "--non-interactive", "install", "libXi6"),
    "pacman": ("pacman", "-S", "--needed", "--noconfirm", "libxi"),
    "apk": ("apk", "add", "libxi"),
}

_DEBIAN = {"debian", "ubuntu", "linuxmint", "pop", "raspbian", "kali", "elementary"}
_RPM = {"rhel", "fedora", "centos", "rocky", "almalinux", "ol", "oracle", "amzn"}
_ARCH = {"arch", "manjaro", "endeavouros", "garuda", "artix"}

# One attempt per process: every root that stages cua-driver after a failure
# would otherwise re-run the package manager under PM's install lock. A later
# process retries.
_ATTEMPT: tuple[bool, str] | None = None


def _release_tokens() -> set[str]:
    try:
        fields = platform.freedesktop_os_release()
    except OSError:
        return set()
    blob = f"{fields.get('ID', '')} {fields.get('ID_LIKE', '')}".lower()
    return set(blob.replace(",", " ").split())


def _manager_order(tokens: set[str]) -> tuple[str, ...]:
    if tokens & _DEBIAN:
        return ("apt-get",)
    if tokens & _RPM:
        return ("dnf", "yum")
    if any("suse" in token or token.startswith("sles") for token in tokens):
        return ("zypper",)
    if tokens & _ARCH:
        return ("pacman",)
    if "alpine" in tokens:
        return ("apk",)
    return ("dnf", "yum", "apt-get", "zypper", "pacman", "apk")


def _host_install_command() -> tuple[str, ...] | None:
    for manager in _manager_order(_release_tokens()):
        if shutil.which(manager):
            return _INSTALLERS[manager]
    return None


def _is_root() -> bool:
    return bool(hasattr(os, "geteuid") and os.geteuid() == 0)


def _command_plan(command: tuple[str, ...]) -> tuple[list[str] | None, str, str]:
    """Return auto-repair argv, its display form, and a runnable manual remedy.

    Host-package repair runs while PM owns its publication lock, so it must never
    wait on an interactive privilege prompt. Non-root repair therefore uses
    ``sudo -n`` even on a TTY. The manual remedy may use normal ``sudo``
    outside that lock. If sudo is unavailable, don't advertise it at all.
    """
    if _is_root():
        argv = list(command)
        shown = shlex.join(argv)
        return argv, shown, shown
    sudo = shutil.which("sudo")
    if sudo:
        argv = [sudo, "-n", *command]
        return argv, shlex.join(["sudo", "-n", *command]), shlex.join(["sudo", *command])
    return None, "", f"as root: {shlex.join(command)}"


def _run(argv: list[str], stdin: int | None = subprocess.DEVNULL, timeout: float | None = 300) -> bool:
    try:
        return subprocess.run(argv, stdin=stdin, timeout=timeout, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _install(prefix: list[str], command: tuple[str, ...], stdin: int | None = subprocess.DEVNULL,
             timeout: float | None = 300) -> bool:
    if _run([*prefix, *command], stdin, timeout):
        return True
    if command[0] != "apt-get":
        return False
    # Minimal Debian/Ubuntu images ship empty package lists.
    return (_run([*prefix, "apt-get", "update", "-qq"], stdin, timeout)
            and _run([*prefix, *command], stdin, timeout))


def try_install_libxi() -> tuple[bool, str]:
    """Try the distro-native libXi package; return (attempt_succeeded, hint).

    Success means the package-manager command completed successfully. The
    cua-driver smoke probe remains the authority and is always repeated by the
    caller.
    """
    global _ATTEMPT
    if _ATTEMPT is None:
        _ATTEMPT = _attempt()
    return _ATTEMPT


def _attempt() -> tuple[bool, str]:
    command = _host_install_command()
    if command is None:
        return (
            False,
            "cua-driver needs libXi.so.6; install the distro package that provides it and rerun",
        )

    argv, attempt_display, remedy_display = _command_plan(command)
    remedy = f"install the missing runtime library with {remedy_display} and rerun"
    if argv is None:
        return False, remedy

    print(f"→ cua-driver needs libXi.so.6; trying non-interactive {attempt_display}", flush=True)
    return _install(argv[: len(argv) - len(command)], command), remedy
