"""The install/update E2E clean-checkout assertion.

Regression (stable release rc.3-v0.23.6, run 46024985528, 2026-11-27):
the linux HEAD -> NEXT leg failed its stage phase with 'checkout has
uncommitted tracked changes' although nothing had changed. The culprit
is scripts/install.ps1, the repo's only file whose blob stores CRLF
while .gitattributes says `*.ps1 text eol=crlf`: once anything
invalidates git's stat cache for it, git re-hashes it and reports the
whole file modified. The assertion must tolerate CR-at-EOL-only
differences (a bare clone serves committed objects, so they cannot leak
into serve.git) while still failing on real changes -- and naming the
file when it fails.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "tests" / "install" / "e2e-assets" / "assert-clean-checkout.sh"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=check, timeout=30)


def _crlf_fixture_repo(path: Path) -> Path:
    """A repo with a CRLF-blob .ps1 file, like the real one: the file is
    committed BEFORE .gitattributes exists, so the blob keeps its CRLF.
    A touch then invalidates git's stat cache for it, so `git status`
    reports exactly ` M install.ps1` with no content changed -- the same
    exposure a checkout race causes in CI (whether the bare attributes
    commit alone exposes it is timing-dependent, so the touch makes the
    fixture deterministic)."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, timeout=30)
    (path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (path / "install.ps1").write_bytes(b"line1\r\nline2\r\n")
    _git(path, "add", "app.py", "install.ps1")
    _git(path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    (path / ".gitattributes").write_text("*.ps1 text eol=crlf\n", encoding="utf-8")
    _git(path, "add", ".gitattributes")
    _git(path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "attributes")
    (path / "install.ps1").touch()
    assert _git(path, "status", "--porcelain", "-uno").stdout == " M install.ps1\n"
    return path


def _plain_fixture_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, timeout=30)
    (path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    _git(path, "add", "app.py")
    _git(path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    assert _git(path, "status", "--porcelain", "-uno").stdout == ""
    return path


def _check(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f'source "{HELPER}" && assert_clean_checkout "{repo}"'],
        capture_output=True, text=True, timeout=30, check=False)


def test_cr_only_worktree_difference_passes(tmp_path):
    repo = _crlf_fixture_repo(tmp_path / "crlf")
    assert _check(repo).returncode == 0
    # A genuinely clean tree passes too.
    assert _check(_plain_fixture_repo(tmp_path / "plain")).returncode == 0


def test_real_worktree_change_fails_and_names_the_file(tmp_path):
    repo = _plain_fixture_repo(tmp_path / "plain")
    (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
    result = _check(repo)
    assert result.returncode == 1
    assert "checkout has uncommitted tracked changes" in result.stderr
    assert "app.py" in result.stderr
    # The same real change, staged, must fail too.
    _git(repo, "add", "app.py")
    result = _check(repo)
    assert result.returncode == 1
    assert "app.py" in result.stderr
    # And a real change must fail even on top of the CR-only artifact:
    # the tolerance must not mask a genuine modification.
    crlf_repo = _crlf_fixture_repo(tmp_path / "crlf")
    (crlf_repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
    result = _check(crlf_repo)
    assert result.returncode == 1
    assert "app.py" in result.stderr
