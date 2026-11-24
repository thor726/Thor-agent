"""Shared dollar-denominated usage model for the ``/usage`` and ``/subscription`` bars.

Terminal surfaces show **dollars**, never "credits"; the plan allowance and top-up
dollars stay distinctly visible as two SEPARATE bars (a three-segment bar is
unreadable at terminal widths). Source: ``ThorHubAccountInfo.paid_service_access_info``
(USD floats despite the legacy ``*_credits`` names) plus ``subscription.monthly_credits``
(plan bar denominator) and ``current_period_end``. Fail-open: missing/non-finite fields
degrade to fewer bars; logged-out / unreachable portal yields ``available=False``.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import asdict, dataclass, fields
from typing import Any, Optional

from thor_time import safe_strftime

logger = logging.getLogger(__name__)

# Below this TOTAL spendable ($) a paid account is flagged "low" — the alert state
# that nudges top-up/upgrade before a mid-run cutoff (product: "below $5 is an alert").
LOW_BALANCE_THRESHOLD_USD = 5.0


def _finite(value: Any) -> Optional[float]:
    """Float iff a real finite number (not bool/NaN/Inf); json.loads admits bare NaN, which would render ``$nan``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def _fmt_usd(value: Optional[float]) -> str:
    """``$X,XXX.YY`` for display. ``None`` -> ``$0.00`` (callers gate on presence)."""
    return f"${(value or 0.0):,.2f}"


def format_renews(value: Optional[str]) -> Optional[str]:
    """ISO date/timestamp -> ``Jul 24, 2026``; unparseable input is returned unchanged."""
    from datetime import datetime
    text = str(value or "").strip()
    if not text:
        return None
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        try:
            dt = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return text
    # %-d isn't portable to Windows; build the day without a leading zero.
    return f"{safe_strftime(dt, '%b')} {dt.day}, {dt.year}"


@dataclass(frozen=True)
class UsageBar:
    """One bar: ``spent`` of ``total`` plus remaining. ``plan`` shows % used; ``topup`` has no
    denominator (``spent`` is 0 and ``total == remaining`` so it renders full)."""

    kind: str  # "plan" | "topup"
    remaining_usd: float
    total_usd: float
    spent_usd: float = 0.0

    @property
    def pct_used(self) -> Optional[int]:
        if self.kind != "plan" or self.total_usd <= 0:
            return None
        return max(0, min(100, round(self.spent_usd / self.total_usd * 100)))

    @property
    def fill_fraction(self) -> float:
        """Fraction of the bar that should read as 'remaining' (filled)."""
        return max(0.0, min(1.0, self.remaining_usd / self.total_usd)) if self.total_usd > 0 else 0.0


@dataclass(frozen=True)
class UsageModel:
    """Dollar usage model shared by /usage and /subscription. ``status``: ``free`` (no plan / no
    paid access), ``low`` (spendable < $5, ALERT), ``healthy`` (>= $5), ``depleted`` (paid access lost)."""

    available: bool
    status: str = "free"
    plan_name: Optional[str] = None
    renews_at: Optional[str] = None
    renews_display: Optional[str] = None
    subscription_remaining_usd: Optional[float] = None
    topup_remaining_usd: Optional[float] = None
    total_spendable_usd: Optional[float] = None
    plan_bar: Optional[UsageBar] = None
    topup_bar: Optional[UsageBar] = None

    @property
    def has_topup(self) -> bool:
        return bool(self.topup_remaining_usd and self.topup_remaining_usd > 0)


def usage_model_wire(model: Optional[UsageModel]) -> Optional[dict]:
    """The model as ``session.account_usage``'s ``nous_usage`` (numbers, not display strings); None when unavailable."""
    return asdict(model) if model is not None and model.available else None


def usage_model_from_wire(value: Any) -> Optional[UsageModel]:
    """:func:`usage_model_wire`'s dict back to a model; None for anything else. Unknown keys from a newer owner are dropped."""
    if not isinstance(value, dict):
        return None
    known = {f.name for f in fields(UsageModel)}
    bars = {key: UsageBar(**bar) if isinstance(bar := value.get(key), dict) else None for key in ("plan_bar", "topup_bar")}
    return UsageModel(**{**{k: v for k, v in value.items() if k in known}, **bars})


def build_usage_model(*, timeout: float = 10.0) -> UsageModel:
    """Build the usage model; fail-open. ``THOR_DEV_CREDITS_FIXTURE`` short-circuits to a fixture.
    The Nous Portal account fetch that used to feed this is gone; without a fixture there is no
    dollar usage model anymore (the ThorHub balance lives on /topup)."""
    fixture = _dev_fixture_usage_model()
    if fixture is not None:
        return fixture
    return UsageModel(available=False)


def _plan_bar(remaining: float, spent: float) -> UsageBar:
    return UsageBar(kind="plan", remaining_usd=remaining, total_usd=20.0, spent_usd=spent)


def _dev_fixture_usage_model() -> Optional[UsageModel]:
    """``THOR_DEV_CREDITS_FIXTURE`` -> fixture model (``free|healthy|low|topup|depleted``), else None."""
    name = (os.getenv("THOR_DEV_CREDITS_FIXTURE") or "").strip().lower()
    name = {"mid": "healthy", "top-up": "topup"}.get(name, name)
    plus = dict(available=True, plan_name="Plus", renews_at="2026-07-01")
    specs: dict[str, dict] = {
        "free": dict(available=True, status="free", plan_name=None),
        "healthy": dict(**plus, status="healthy", subscription_remaining_usd=14.0, total_spendable_usd=14.0, plan_bar=_plan_bar(14.0, 6.0)),
        "topup": dict(
            **plus, status="healthy", subscription_remaining_usd=14.0, topup_remaining_usd=12.0,
            total_spendable_usd=26.0, plan_bar=_plan_bar(14.0, 6.0),
            topup_bar=UsageBar(kind="topup", remaining_usd=12.0, total_usd=12.0, spent_usd=0.0),
        ),
        "low": dict(**plus, status="low", subscription_remaining_usd=3.4, total_spendable_usd=3.4, plan_bar=_plan_bar(3.4, 16.6)),
        "depleted": dict(**plus, status="depleted", subscription_remaining_usd=0.0, total_spendable_usd=0.0, plan_bar=_plan_bar(0.0, 20.0)),
    }
    spec = specs.get(name)
    return UsageModel(**spec) if spec else None
