"""Guest handoff — RETIRED with the Nous Portal (Fase 4 debrand).

When a Portal sign-in replaced a guest free tier, this module moved the guest's apps to the new
account (``POST {portal}/api/anonymous/claim``) and kept a retry worker. The Portal is gone, so
no handoff can ever run: :func:`drain` returns nothing, the status endpoints answer "none", and
:func:`note_store_write` is a no-op. The public names are kept so ``thor_cli.auth`` (which calls
``note_store_write`` on every provider-state save) and the web routers keep resolving.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

PENDING = "pending"
RETRYING = "retrying"
HANDOFF_FILENAME = "guest_handoff.json"
CLAIM_TIMEOUT_SECONDS = 10.0


def note_store_write(auth_store: dict[str, Any], provider_id: str, state: Any) -> None:
    """No-op: there is no guest state to hand off anymore."""
    return


def note_replacement(previous: Any, new: Any) -> None:
    return None


def drain() -> list[dict[str, Any]]:
    """No handoff is ever pending."""
    return []


def handoff_status() -> Optional[dict[str, Any]]:
    return None


def wire_status(record: Optional[dict[str, Any]]) -> dict[str, Any]:
    """The wire shape the long-poll endpoint renders: always "none" (no handoff exists)."""
    return {"status": "none", "updated_at": None}


def result_lines(view: dict[str, Any]) -> tuple[str, ...]:
    return ()


def record_status(anon_token: str) -> Optional[dict[str, Any]]:
    return None


def start_worker() -> threading.Thread:
    """No worker: returns an unstarted thread so callers that hold it keep working."""
    return threading.Thread(target=lambda: None, name="guest-handoff-retired", daemon=True)
