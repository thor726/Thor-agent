"""Free managed Perplexity fast search for a ThorHub identity: the route exists only when an
explicit ``PERPLEXITY_GATEWAY_URL`` names a gateway and a usable ThorHub key is present. The
gateway serves ``POST /search`` + ``search_type: "fast"`` without funding checks, so the local
paid-tool gate must not block this one route while every other managed vendor keeps it. Real
config, real auth store, real selection-to-provider dispatch over local HTTP."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from tests.thor_cli.anon_portal import as_local_desktop_backend

# A ThorHub identity: a static API key in the auth store. There is no guest or
# anonymous tier anymore — a legacy Nous JWT entitles nothing.
THORHUB_KEY = "sk-thor-test"


def _thorhub_state() -> dict:
    return {"api_key": THORHUB_KEY}


@pytest.fixture
def gateway_server(monkeypatch):
    class Log(list):
        base = ""

    requests = Log()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, dict(self.headers), body))
            ok = self.path in ("/perplexity/search", "/direct/search")
            content = json.dumps({"results": [{"title": "t", "url": "https://example.test", "snippet": "s"}]}
                                 if ok else {"error": "payment required"}).encode()
            self.send_response(200 if ok else 402)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    requests.base = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("PERPLEXITY_GATEWAY_URL", requests.base + "/perplexity")
    monkeypatch.setenv("PERPLEXITY_BASE_URL", requests.base + "/direct")
    monkeypatch.setenv("FIRECRAWL_GATEWAY_URL", requests.base)
    monkeypatch.setattr("tools.web_tools._firecrawl_client", None, raising=False)
    try:
        yield requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _write_home(home, monkeypatch, *, thorhub_state=None, config=None):
    from thor_cli.config import atomic_config_write
    from thor_cli.thorhub_account import reset_thorhub_account_info_cache

    home.mkdir(parents=True)
    monkeypatch.setenv("THOR_HOME", str(home))
    as_local_desktop_backend(monkeypatch)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("TOOL_GATEWAY_USER_TOKEN", raising=False)
    atomic_config_write(home / "config.yaml", {"web": {"keyless_rescue": False}, **(config or {})})
    if thorhub_state is not None:
        (home / "auth.json").write_text(json.dumps({"version": 1, "providers": {"thor": thorhub_state}}))
    reset_thorhub_account_info_cache()


def _search():
    from tools import web_tools
    from tests.tools.conftest import register_all_web_providers

    register_all_web_providers()
    return json.loads(web_tools.web_search_tool("free fast search", limit=3))


def _calls(log):
    return [(path, headers["Authorization"], body.get("search_type")) for path, headers, body in log]


def test_thorhub_identity_autodetects_free_fast_search(monkeypatch, tmp_path, gateway_server):
    """A ThorHub key + an explicit gateway URL reach the gateway, while the paid gate
    stays closed for extract and every other vendor."""
    from thor_cli.thorhub_account import get_thorhub_account_info
    from tools import web_tools
    from tools.tool_backend_helpers import managed_thorhub_tools_enabled

    _write_home(tmp_path / "home", monkeypatch, thorhub_state=_thorhub_state())
    # Premise: ThorHub has no anonymous tier and no default managed gate; the
    # fixture's explicit FIRECRAWL_GATEWAY_URL makes the firecrawl route
    # available, while extract stays off Perplexity.
    assert get_thorhub_account_info().is_anonymous_tier is False
    assert managed_thorhub_tools_enabled() is False
    assert web_tools.check_firecrawl_api_key() is True
    assert web_tools._get_extract_backend() != "perplexity"

    result = _search()

    assert result["success"] is True, result
    assert _calls(gateway_server) == [("/perplexity/search", f"Bearer {THORHUB_KEY}", "fast")]


def test_free_fast_search_failure_skips_paid_firecrawl_but_keeps_keyless_rescue(monkeypatch, tmp_path, gateway_server):
    from plugins.web import keyless_mcp

    state = _thorhub_state()
    _write_home(tmp_path / "home", monkeypatch, thorhub_state=state, config={"web": {"keyless_rescue": True}})
    monkeypatch.setenv("PERPLEXITY_GATEWAY_URL", gateway_server.base + "/down")
    rescued = {"success": True, "data": {"web": [{"title": "ring", "url": "https://ring.test", "description": "", "position": 1}]}}
    monkeypatch.setattr(keyless_mcp, "search_with_failover", lambda *a, **kw: dict(rescued, data=dict(rescued["data"])))

    result = _search()

    assert result["data"]["rescued_from"] == "perplexity"
    assert _calls(gateway_server) == [("/down/search", f"Bearer {THORHUB_KEY}", "fast")]


@pytest.mark.parametrize("state,config", [
    (None, {}),
    (None, {"web": {"search_backend": "exa"}}),
])
def test_free_fast_search_needs_a_usable_identity_and_no_explicit_selection(monkeypatch, tmp_path, gateway_server, state, config):
    from tools import web_tools

    _write_home(tmp_path / "home", monkeypatch, thorhub_state=state, config=config)

    assert web_tools._managed_web_search() is False
    assert web_tools._get_search_backend() != "perplexity"


def test_direct_perplexity_key_beats_free_fast_search(monkeypatch, tmp_path, gateway_server):
    _write_home(tmp_path / "home", monkeypatch, thorhub_state=_thorhub_state())
    monkeypatch.setenv("PERPLEXITY_API_KEY", "direct-key")

    assert _search()["success"] is True
    assert _calls(gateway_server) == [("/direct/search", "Bearer direct-key", None)]


def test_free_fast_search_eligibility_follows_the_served_profile(monkeypatch, tmp_path, gateway_server):
    """Multiplex A→B→A: profile A holds a ThorHub key, B none; each answers from its own store."""
    from thor_cli.thorhub_account import reset_thorhub_account_info_cache
    from agent.secret_scope import set_multiplex_active
    from gateway.run import _profile_runtime_scope
    from tools import web_tools

    root = tmp_path / ".thor"
    profile_a, profile_b = root / "profiles" / "a", root / "profiles" / "b"
    _write_home(profile_a, monkeypatch, thorhub_state=_thorhub_state(), config={"web": {"keyless_fallback": False}})
    _write_home(profile_b, monkeypatch, config={"web": {"keyless_fallback": False}})
    monkeypatch.setenv("THOR_HOME", str(root))
    (root / "config.yaml").write_text("")
    set_multiplex_active(True)
    try:
        seen = []
        for home in (profile_a, profile_b, profile_a):
            reset_thorhub_account_info_cache()
            with _profile_runtime_scope(home):
                seen.append(web_tools._get_search_backend())
    finally:
        set_multiplex_active(False)
    assert seen[0] == seen[2] == "perplexity"
    assert seen[1] != "perplexity"