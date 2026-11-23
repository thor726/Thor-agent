"""``/topup`` balance view, ThorHub edition.

The only money surface Thor still has is ThorHub (llm.thormarket.site):
``/topup`` shows the token balance of the configured ThorHub key and hands
the buyer the top-up link. There is no Nous Portal account anymore — the
old ``agent.account_usage_nous`` module (portal fetch, dollar credits,
usage windows, subscriptions) was deleted with it; this module replaces
only the ``/topup`` view (``CreditsView`` / ``build_credits_view``) that
the CLI, the gateway and the TUI shared.

Fail-open: no key / fetch fails -> ``CreditsView(logged_in=False)``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreditsView:
    """Surface-agnostic ``/topup`` balance view: one ThorHub fetch, consumed identically by every money surface.
    Fail-open: no key / ThorHub unreachable -> ``logged_in`` False, ``topup_url`` None."""

    logged_in: bool
    balance_lines: tuple[str, ...] = ()
    identity_line: Optional[str] = None
    topup_url: Optional[str] = None
    depleted: bool = False


def _thorhub_credits_view() -> Optional[CreditsView]:
    """``/topup`` versi ThorHub: saldo token dari ThorHub bila THORHUB_API_KEY ada.

    None bila tidak ada key / fetch gagal.
    """
    try:
        from thor_cli.thorhub_account import (
            THORHUB_TOPUP_URL,
            fetch_thorhub_balance,
            format_thorhub_balance_lines,
        )
    except Exception:
        return None
    try:
        data = fetch_thorhub_balance()
    except Exception:
        return None
    if not data:
        return None
    who = [str(v) for v in (data.get("user_name"),) if v]
    return CreditsView(
        logged_in=True,
        balance_lines=format_thorhub_balance_lines(data),
        identity_line=("ThorHub · " + " / ".join(who)) if who else "ThorHub",
        topup_url=THORHUB_TOPUP_URL,
        depleted=bool(data.get("tokens_remaining") == 0),
    )


def build_credits_view(*, markdown: bool = False, timeout: float = 10.0) -> CreditsView:
    """/topup view: ThorHub balance block + identity line + top-up URL.
    Fail-open -> ``CreditsView(logged_in=False)``."""
    return _thorhub_credits_view() or CreditsView(logged_in=False)
