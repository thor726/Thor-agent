"""The Webapp's gateway socket answers for the profile its ticket names, on a multiplexed gateway.

A browser tab's ``/api/ws`` reaches the gateway through the dashboard mount (``chat_ws.gateway_ws``),
not the native ticket path (``gateway/run_api.py``) that wraps the socket in ``owner_scope``. The
authority answers ``-32601`` for ``billing.state``, so the frame falls back to the legacy handler,
which reads the ThorHub base URL through the socket's scope: unbound, a multiplexed gateway
refused the read (``UnscopedSecretError`` -> "no profile secret scope on a multiplexed call") and the
key went to the default ThorHub host. ``dispatch_legacy`` binds a non-launch ticket's profile; a
launch-profile socket relies on ``gateway_ws``'s own scope.

Real ``gateway_ws``, ``handle_ws``, session authorities, legacy fallback and billing handler; only
the upgrade gate (which stamps the ticket's identity and home on the socket) and HTTP are substituted.
"""

import asyncio
import io
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from starlette.websockets import WebSocketDisconnect


def _home(home, label):
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text("model:\n  provider: thor\n  default: fixture-model\n")
    (home / ".env").write_text(f"THORHUB_BASE_URL=https://{label}-portal.invalid\n")
    (home / "auth.json").write_text(json.dumps({"version": 1, "providers": {"thor": {
        "api_key": f"sk-thor-{label}",
    }}}))


@pytest.fixture
def gateway(tmp_path, monkeypatch):
    """A multiplexed runner serving the launch home and profile ``b``, each with its own authority."""
    from agent import secret_scope
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import SessionAuthority
    from thor_cli import auth, thorhub_account, thorhub_billing
    from thor_state import SessionDB
    from thor_state_runtime import begin_runtime_epoch
    from tui_gateway import launch_profile_policy, server

    launch, b = tmp_path / "launch", tmp_path / "launch" / "profiles" / "b"
    _home(launch, "launch")
    _home(b, "b")
    monkeypatch.setenv("THOR_HOME", str(launch))
    monkeypatch.setenv("THOR_SHARED_AUTH_DIR", str(tmp_path / "shared-auth"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for key in ("THORHUB_BASE_URL", "THOR_PORTAL_BASE_URL", "NOUS_PORTAL_BASE_URL", "NOUS_INFERENCE_BASE_URL",
                "THOR_DEV_BILLING_FIXTURE", "THOR_DEV_SUBSCRIPTION_FIXTURE", "THOR_DEV_CREDITS_FIXTURE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(launch_profile_policy, "_snapshot", None)
    monkeypatch.setattr(server, "_thor_home", str(launch))
    monkeypatch.setattr(server, "_served_profile_homes", set())
    monkeypatch.setattr(auth, "_RESOLVE_TOKEN_CACHE", {})
    thorhub_account.reset_thorhub_account_info_cache()
    previous = secret_scope.is_multiplex_active()
    launch_profile_policy.activate_multi_profile_hosting()

    by_home, dbs = {}, []
    runner = SimpleNamespace(_draining=False, config=SimpleNamespace(multiplex_profiles=True))
    runner.session_authorities = SimpleNamespace(for_home=lambda home: by_home.get(Path(home).resolve()))
    for home in (launch, b):
        db = SessionDB(home / "state.db")
        dbs.append(db)
        store = SessionStore(config=GatewayConfig(), sessions_dir=home / "sessions")
        store._db = db
        runner.session_store = store
        by_home[home.resolve()] = SessionAuthority(runner, profile_id=str(home), instance_id="first", db=db,
                                                   epoch=begin_runtime_epoch(db, instance_id="first"))
    runner.session_authority = by_home[launch.resolve()]

    portal_hits = []

    def urlopen(request, *args, **kwargs):
        portal_hits.append(urlsplit(request.full_url).hostname)
        response = io.BytesIO(json.dumps({"data": {
            "tokens_remaining": 5000, "token_limit": 10000, "tokens_used": 5000, "is_active": True,
        }}).encode())
        response.status = 200
        return response
    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    from thor_cli import mcp_startup
    from thor_cli.web_routers import chat_ws

    async def allowed(*_a, **_k):
        return True
    monkeypatch.setattr(chat_ws, "_close_unless_sidecar_allowed", allowed)
    monkeypatch.setattr(mcp_startup, "start_deferred_mcp_discovery_now", lambda: None)
    try:
        yield SimpleNamespace(launch=launch, b=b, authority=runner.session_authority, portal_hits=portal_hits)
    finally:
        secret_scope.set_multiplex_active(previous)
        for db in dbs:
            db.close()


class _Socket:
    """An accepted ``/api/ws`` connection carrying what the upgrade gate stamps on a Webapp ticket."""

    def __init__(self, authority, frames, ticket_home=None):
        self.app = SimpleNamespace(state=SimpleNamespace(session_authority=authority))
        self.scope, self.client, self.closed, self.sent = {}, None, None, []
        self._thor_auth_identity = {"user_id": "owner", "provider": "session-token"}
        self._thor_ticket_profile_home = None if ticket_home is None else str(ticket_home)
        self._frames = [json.dumps(frame) for frame in frames]
        self._answered = asyncio.Event()

    async def accept(self, subprotocol=None):
        pass

    async def close(self, code=None):
        self.closed = code

    async def send_text(self, text):
        frame = json.loads(text)
        self.sent.append(frame)
        if frame.get("id") is not None:
            self._answered.set()

    async def receive_text(self):
        if self._frames:
            return self._frames.pop(0)
        await asyncio.wait_for(self._answered.wait(), 20)
        raise WebSocketDisconnect(1000)

    def reply(self, req_id):
        return next(frame for frame in self.sent if frame.get("id") == req_id)


def _billing_state_over_socket(gateway, ticket_home):
    from thor_cli.web_routers import chat_ws
    ws = _Socket(gateway.authority, [{"jsonrpc": "2.0", "id": "bill", "method": "billing.state", "params": {}}],
                 ticket_home)
    gateway.portal_hits.clear()
    asyncio.run(chat_ws.gateway_ws(ws))
    assert ws.closed is None, ws.closed
    return ws.reply("bill"), list(gateway.portal_hits)


def test_billing_state_on_a_webapp_socket_reaches_its_tickets_profile_portal(gateway, caplog):
    with caplog.at_level(logging.WARNING):
        seen = [_billing_state_over_socket(gateway, home) for home in (gateway.b, gateway.launch, gateway.b)]

    for (reply, hits), label in zip(seen, ("b", "launch", "b")):
        assert reply["result"]["logged_in"] is True, reply
        assert hits and set(hits) == {f"{label}-portal.invalid"}, (label, hits)
    assert "no profile secret scope" not in caplog.text


def test_a_profile_ticket_with_no_authority_bound_is_refused_not_served_as_the_launch_profile(gateway):
    from thor_cli.web_routers import chat_ws
    ws = _Socket(None, [{"jsonrpc": "2.0", "id": "bill", "method": "billing.state", "params": {}}], gateway.b)

    asyncio.run(chat_ws.gateway_ws(ws))

    assert ws.closed == 1013
    assert ws.sent == [] and gateway.portal_hits == []
