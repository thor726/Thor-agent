"""install.ps1's self-contained PowerShell suites, under Windows PowerShell 5.1 and pwsh 7.

``scripts/tests/*.ps1`` drive the real installer as a subprocess and exit
non-zero on any failed assertion. install.ps1 is delivered via ``irm | iex``
into whatever shell the user already has, and 5.1 is what ships with Windows,
so each suite runs under both: a construct that only parses under 7 is a broken
installer for most of the people hitting it.

pwsh 7 is a runner-image extra, not a Windows guarantee: `windows-latest`
carries it, a container or a stripped image need not. Its absence is
therefore a skip, not a failure — failing here reported a missing tool as a
broken installer and took the whole Windows lane red with it. Nothing is
silently lost: the 5.1 half of every pair still runs unconditionally, and
`test_replay_...`-style coverage of the 7-only constructs belongs in the
suite itself, not in this runner's tool list.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.platforms("windows")
SUITES = Path(__file__).resolve().parents[3] / "scripts" / "tests"
# Per-suite budget for one shell. The suites drive the real installer, whose
# stages download; a cold runner is slower than a developer box and the
# runner's own per-FILE cap (scripts/run_tests_parallel.py, 300 s default)
# applies to the whole collected file, so a large per-suite timeout here
# cannot save the file — it only turns a clean "timed out" into a report that
# names nothing. Keep this well under the file cap.
_SUITE_TIMEOUT = 120


def _shell(name: str) -> str:
    if name == "powershell":
        return str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
    found = shutil.which("pwsh")
    if not found:
        pytest.skip("PowerShell 7 (pwsh) is not installed on this host")
    return found


@pytest.mark.parametrize("shell", ["powershell", "pwsh"])
@pytest.mark.parametrize("suite", sorted(p.name for p in SUITES.glob("test-install-ps1-*.ps1")))
def test_suite_passes(shell, suite):
    result = subprocess.run([_shell(shell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(SUITES / suite)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=_SUITE_TIMEOUT, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
