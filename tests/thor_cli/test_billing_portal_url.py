"""Portal-URL resolution for ThorHub billing errors.

The server emits ``portalUrl`` relative by design (``/beli/topup``); the client must
resolve it against the active ThorHub base so deep-links are clickable on whatever
deployment (staging / prod) the user is pointed at. ThorHub has no billing HTTP API,
so there is no HTTP -> exception mapping to test here — write paths raise
``BillingError`` with the topup URL (see test_thorhub_billing.py).
"""

from __future__ import annotations

import pytest

from thor_cli.thorhub_billing import (
    _absolutize_portal_url,
    resolve_portal_base_url,
)


@pytest.fixture
def _staging(monkeypatch):
    monkeypatch.setenv("THORHUB_BASE_URL", "https://staging.thormarket.site")


def test_absolutize_resolves_relative(_staging):
    assert (
        _absolutize_portal_url("/beli/topup")
        == "https://staging.thormarket.site/beli/topup"
    )


def test_absolutize_passes_absolute_through(_staging):
    assert (
        _absolutize_portal_url("https://llm.thormarket.site/beli/topup")
        == "https://llm.thormarket.site/beli/topup"
    )


def test_absolutize_defaults_to_production(monkeypatch):
    monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
    assert resolve_portal_base_url() == "https://llm.thormarket.site"
    assert (
        _absolutize_portal_url("/beli/topup")
        == "https://llm.thormarket.site/beli/topup"
    )
