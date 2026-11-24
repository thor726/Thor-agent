"""Compatibility shim: checkpoint code moved to :mod:`agent.checkpoints`.

Kept so existing ``tools.checkpoint_*`` imports keep working; new code
should import from :mod:`agent.checkpoints` directly. This module is an
alias for the new location (not a copy): attribute access and
monkeypatching reach the real module.
"""

import sys as _sys

from agent.checkpoints import manager as _new

_sys.modules[__name__] = _new
