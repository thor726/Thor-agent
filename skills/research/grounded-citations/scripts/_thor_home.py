"""Resolve THOR_HOME for standalone skill scripts.

Skill scripts may run outside the Thor process (system Python, nix env,
CI) where ``thor_constants`` is not importable.  This module provides the
same ``get_thor_home()`` contract without requiring it on ``sys.path``.

When ``thor_constants`` IS available it is used directly so profile
resolution and any future enhancements are picked up automatically.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from thor_constants import get_thor_home
except (ModuleNotFoundError, ImportError):

    def get_thor_home() -> Path:
        """Return the Thor home directory (default: ``~/.thor``)."""
        val = os.environ.get("THOR_HOME", "").strip()
        return Path(val) if val else Path.home() / ".thor"
