"""Resolve THOR_HOME for standalone skill scripts.

Skill scripts may run outside the Thor process (e.g. system Python,
nix env, CI) where ``thor_constants`` is not importable.  This module
provides the same ``get_thor_home()`` and ``display_thor_home()``
contracts as ``thor_constants`` without requiring it on ``sys.path``.

When ``thor_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``thor_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``THOR_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from thor_constants import display_thor_home
    from thor_constants import get_thor_home
except (ModuleNotFoundError, ImportError):

    def get_thor_home() -> Path:
        """Return the Thor home directory (default: ~/.thor).

        Mirrors ``thor_constants.get_thor_home()``."""
        val = os.environ.get("THOR_HOME", "").strip()
        return Path(val) if val else Path.home() / ".thor"

    def display_thor_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``thor_constants.display_thor_home()``."""
        home = get_thor_home()
        try:
            return "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(home)
