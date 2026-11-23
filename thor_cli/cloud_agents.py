"""Thor Cloud agents — retired with the Thor Portal.

Cloud agents lived on the Portal (``GET /api/agents``); ThorHub has no cloud-agents API, so
:func:`discover` raises :class:`CloudAgentsError` instead of hitting a dead host.
"""

from __future__ import annotations

from typing import Any, Optional

_TIMEOUT_S = 15.0


# "Unavailable on ThorHub" is a state of this install, not of the caller's dashboard session:
# 409, never 401. Every dashboard client reads a 401 (and the Webapp's AuthWidget a 403) as its own
# session being refused, so a 401 here would send a no-auth Webapp user to the Webapp sign-in page
# instead of telling them the feature is retired.
PORTAL_SIGNIN_STATUS = 409


class CloudAgentsError(RuntimeError):
    def __init__(self, message: str, status: int, code: str):
        super().__init__(message)
        self.status = status
        self.code = code


def discover(org: Optional[str] = None) -> dict[str, Any]:
    """``{agents, org}`` — retired: Thor Cloud agents lived on the Thor Portal, which is gone.

    ThorHub has no cloud-agents API, so the call fails honestly instead of hitting a dead host.
    """
    raise CloudAgentsError(
        "Cloud agents are unavailable on ThorHub — the Thor Portal is retired.",
        PORTAL_SIGNIN_STATUS, "portal_retired")
