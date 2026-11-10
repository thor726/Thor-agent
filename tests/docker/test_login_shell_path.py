"""Login shells in the image keep Thor' own dirs on PATH.

Debian's ``/etc/profile`` resets PATH for every login shell, so without
``/etc/profile.d/thor.sh`` a ``bash -l`` (``docker exec <c> bash -l``, ssh, the
terminal tool's background ``bash -lic``) lost ``/opt/thor/bin`` and bare
``thor`` exited 127 (#56634).
"""
from __future__ import annotations

import subprocess


def test_login_shell_resolves_thor_to_the_image_shim(built_image: str) -> None:
    r = subprocess.run(
        ["docker", "run", "--rm", "-u", "thor", "--entrypoint", "bash", built_image,
         "-lc", 'echo "thor=$(command -v thor)"; echo "path=$PATH"'],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
    assert lines["thor"] == "/opt/thor/bin/thor"
    entries = lines["path"].split(":")
    assert entries.index("/opt/thor/bin") < entries.index("/opt/thor/.venv/bin")
    assert entries.count("/opt/thor/bin") == 1
