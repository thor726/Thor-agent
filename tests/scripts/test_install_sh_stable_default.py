"""A new or rerun install of the official repository lands on the latest stable release.

`thor update` already follows stable for an official checkout that never chose a channel;
the installer has to put a fresh install there too, or new users start on main's tip. The
official URL is redirected to a local origin and `curl` answers the release lookup.

Redirecting the official URL needs two halves, because the string "the official
repository" also has to survive the installer's own gate:

* ``url.<local>.insteadOf = <official>`` is consumed when git resolves a URL *from the
  command line*. It is NOT re-applied to a remote whose URL is already stored in
  ``.git/config``, so a fresh clone plus any later fetch has to be re-pointed by hand
  (``origin`` is set to the local origin right after cloning). Without that, ``--tagged
  False`` stops reaching a stub and starts reaching github.com.
* The installer admits stable only for an origin whose URL *is* the official one
  (``is_official_repo``, and the equivalent gate in install.ps1). Both normalise the
  path case-insensitively, so a mixed-case spelling is still the official repository —
  which is what these cases pin.
"""
from pathlib import Path
import os
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL = "https://github.com/dwisetyabudi15581/Thor-agent.git"

pytestmark = pytest.mark.platforms("posix")


def _git(cwd, *args, env=None):
    return subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env,
    ).stdout.strip()


@pytest.mark.parametrize("side,start,args,tagged,lands", [
    (False, None, [], True, "release"),                 # fresh install: the release, not main's tip
    (False, None, ["--channel", "main"], True, "tip"),  # explicit opt-out: main's tip
    (False, "before", [], True, "release"),             # rerun behind the release: moves forward to it
    (False, "tip", [], True, "tip"),                    # rerun already containing it: never moves back
    (False, None, [], False, None),                     # release tag unreachable: fail, publish nothing
    (False, "before", [], False, "before"),             # ... a rerun keeps its checkout instead
    # The release cut on a release branch, main past the fork point (v0.22.2's shape): main moves
    # back only through `thor update`, whose downgrade guard the installer cannot run.
    (True, "tip", [], True, "tip"),
    (True, "tip", ["--channel", "stable"], True, "tip"),
    (True, "before", [], True, "release"),
])
def test_install_lands_on_the_latest_stable_release(tmp_path, side, start, args, tagged, lands):
    origin, home, bin_dir = tmp_path / "origin", tmp_path / "home", tmp_path / "bin"
    install = home / ".thor" / "thor-agent"
    for d in (origin, home, bin_dir):
        d.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "commit", "-q", "--allow-empty", "-m", "before")
    if side:
        _git(origin, "checkout", "-q", "-b", "release/1.2")
    _git(origin, "commit", "-q", "--allow-empty", "-m", "release")
    commits = {"before": _git(origin, "rev-parse", "HEAD~1"), "release": _git(origin, "rev-parse", "HEAD")}
    if tagged:
        _git(origin, "tag", "-a", "v1.2.3", "-m", "release")
    _git(origin, "checkout", "-q", "main")
    _git(origin, "commit", "-q", "--allow-empty", "-m", "newer")
    commits["tip"] = _git(origin, "rev-parse", "HEAD")
    # `url.<origin>.insteadOf` points the child back at the local origin, and the reverse
    # `url.<official>.insteadOf` is the belt-and-braces half.
    (home / ".gitconfig").write_text(
        f'[url "{origin.as_uri()}"]\n  insteadOf = {OFFICIAL}\n'
        f'[url "{OFFICIAL}"]\n  insteadOf = {OFFICIAL}\n',
        encoding="utf-8")
    (bin_dir / "curl").write_text(
        '#!/bin/sh\ncase "$*" in *api.github.com*) printf \'{\\\n  "tag_name": "v1.2.3",\\\n}\\\n\';; *) exit 22;; esac\n',
        encoding="utf-8")
    (bin_dir / "curl").chmod(0o755)
    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "HOME": str(home), "NO_COLOR": "1",
           "GIT_CONFIG_NOSYSTEM": "1"}
    if start:
        install.parent.mkdir(parents=True)
        _git(tmp_path, "clone", "-q", OFFICIAL, str(install), env=env)
        # A clone records the official URL verbatim: ``insteadOf`` was already consumed
        # resolving the clone's command-line URL, and git never re-applies it to a stored
        # remote. Pointing origin at the local repo is what makes the rerun's fetch local;
        # the installer still reads an origin whose URL spells the official repository.
        _git(install, "remote", "set-url", "origin", OFFICIAL, env=env)
        _git(install, "config", "url." + origin.as_uri() + ".insteadOf", OFFICIAL, env=env)
        _git(install, "checkout", "-q", "--detach", commits[start])

    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install.sh"), "--stage", "repository", "--dir", str(install),
         "--thor-home", str(home / ".thor"), "--non-interactive", *args],
        check=False, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120, env=env,
    )

    if lands is None:
        assert result.returncode != 0 and not install.exists(), result.stdout + result.stderr
        return
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(install, "rev-parse", "HEAD") == commits[lands], result.stdout + result.stderr
    assert _git(install, "status", "--porcelain") == "", result.stdout + result.stderr
