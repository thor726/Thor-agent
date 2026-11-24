"""The desktop Connectors page, the CLI and the agent tool — retired with the guest identity.

Hosted connectors ran on the Nous Portal's managed tool gateway behind a guest identity.
ThorHub has no managed gateway and no guest tier, so the connectors routes report
``CONNECTORS_UNAVAILABLE`` (4031) and nothing is ever created: no identity is minted, no
gateway list runs, no sign-in offer is armed. The page list still answers (``available: false``)
so the UI can render the empty state instead of crashing.
"""

from __future__ import annotations

import json
from argparse import Namespace

import pytest

import tui_gateway.server as srv
from thor_cli import free_tier_offer
from tests.thor_cli.anon_portal import install_portal
from tools.connectors import live

ACCOUNT = {"owner": {"type": "account"}}


class _Response:
    def __init__(self, body):
        self.status_code, self._body, self.headers = 200, body, {}

    def json(self):
        return self._body


@pytest.fixture
def portal(monkeypatch, tmp_path):
    fake = install_portal(monkeypatch, tmp_path)
    live._open.clear()
    yield fake
    live._open.clear()


@pytest.fixture
def connector_portal(monkeypatch):
    """The Portal's connector routes: every request as ``(path, sent a bearer)``."""
    requests = []

    class Transport:
        def request(self, method, url, *, headers=None, json=None, timeout=None):
            path = "/" + url.split("://", 1)[1].split("/", 1)[1]
            requests.append((path, "Authorization" in (headers or {})))
            return _Response({"accounts": []} if path.endswith("/accounts") else {"connectors": []})

    monkeypatch.setattr("tools.connectors.portal.client._default_transport", Transport)
    return requests


class _Lists(list):
    connected = False


@pytest.fixture
def gateway(monkeypatch):
    """The connector gateway: every list call, and an instant connect. ``connected`` is what it lists."""
    lists = _Lists()

    class Gateway:
        def __init__(self, **_):
            pass

        def list_connectors(self, *, timeout=None):
            lists.append(1)
            return [{"connector": "notion", "enabled": True, "connected": lists.connected}]

        def connections(self, names, **_):
            return {"results": [{"connector": name, "status": "active", "connection_id": "c1"} for name in names]}

    monkeypatch.setattr("tools.connectors.gateway.client.ConnectorClient", Gateway)
    return lists


def _call(method: str, params: dict | None = None) -> dict:
    return srv.handle_request({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})


def _unavailable(method: str, params: dict | None = None) -> dict:
    response = _call(method, params)
    assert response["error"]["code"] == 4031, response
    assert response["error"]["message"] == "Connectors are not available."
    return response


def test_opening_the_page_creates_no_identity_and_reports_unavailable(portal, connector_portal, gateway):
    assert _call("connectors.list", ACCOUNT)["result"] == {"available": False, "connectors": []}
    for method in ("connectors.catalog", "connectors.accounts", "connectors.policy.get"):
        _unavailable(method)
    assert connector_portal == []
    assert portal.creates() == 0 and gateway == []


def test_connect_is_refused_and_creates_no_identity(portal, connector_portal, gateway, monkeypatch):
    monkeypatch.setattr(free_tier_offer, "_clock", lambda: 1_000_000.0)
    _unavailable("connectors.connect", {**ACCOUNT, "connectors": ["notion"]})
    assert portal.creates() == 0 and gateway == []
    assert "connector_nudge_due_in" not in _call("free_tier.status")
    assert free_tier_offer.offer_due_in(free_tier_offer.CONNECTOR) is None


@pytest.mark.parametrize("entry", ["cli", "agent"])
def test_explicit_lists_report_connectors_unavailable(portal, gateway, entry):
    from thor_cli.connectors_cmd import cmd_connectors
    from tools.connectors.gateway.config import connectors_available
    from tools.connectors.tool import manage_connections

    if entry == "cli":
        assert cmd_connectors(Namespace(connectors_action="list")) == 1
    else:
        result = json.loads(manage_connections({"action": "status"}, connectors_available=connectors_available))
        assert result == {"error": "Connectors are not available in this session."}

    assert portal.creates() == 0 and gateway == []


def test_a_connected_app_sighting_arms_no_offer(portal, gateway, monkeypatch):
    """A list read that shows a connected app still arms nothing: there is no guest to offer to."""
    from tools.connectors.gateway.config import connectors_available
    from tools.connectors.tool import manage_connections

    monkeypatch.setattr(free_tier_offer, "_clock", lambda: 1_000_000.0)
    gateway.connected = True

    for _ in range(2):
        manage_connections({"action": "status"}, connectors_available=connectors_available)

    assert free_tier_offer.offer_due_in(free_tier_offer.CONNECTOR) is None
    assert portal.creates() == 0
