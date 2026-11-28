"""The macOS desktop-installer leg fails fast with no dmg-url configured.

No Thor-Setup.dmg is published anywhere (the bootstrap .dmg is built
as a run artifact only, never published), so the dmg-url default is
empty and the workflow skips those legs. A direct driver run with an
empty URL must fail at the guard with a clear message instead of
failing on an unresolvable download URL.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
DRIVER = ROOT / "tests" / "install" / "macos-desktop-e2e.sh"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(DRIVER), *args], capture_output=True,
                          text=True, timeout=60, check=False)


@pytest.mark.platforms("posix")
def test_empty_dmg_url_fails_fast_with_a_clear_message():
    result = _run("--phase", "install", "--update-method", "open-app-update",
                  "--install-ref", "v0.23.5", "--dmg-url", "")
    assert result.returncode != 0
    assert "no dmg-url configured" in result.stderr


@pytest.mark.platforms("posix")
def test_nonempty_dmg_url_passes_the_guard():
    result = _run("--phase", "install", "--update-method", "open-app-update",
                  "--install-ref", "v0.23.5",
                  "--dmg-url", "https://example.invalid/Thor-Setup.dmg")
    # No staged STATE exists here, so the phase still fails -- but past
    # the guard, not at it.
    assert result.returncode != 0
    assert "no dmg-url configured" not in result.stderr
