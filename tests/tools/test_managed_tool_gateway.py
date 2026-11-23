"""Tests for tools/managed_tool_gateway.py (ThorHub era).

ThorHub runs no default managed gateway: resolve_* report "not available"
unless the user explicitly configured a ``{VENDOR}_GATEWAY_URL`` override
(a self-hosted gateway). The bearer is the static ThorHub key, attached
only to an explicitly configured gateway origin.
"""
import os
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest.mock import patch

from tools import managed_gateway_auth


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "managed_tool_gateway.py"
MODULE_SPEC = spec_from_file_location("managed_tool_gateway_test_module", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
managed_tool_gateway = module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = managed_tool_gateway
MODULE_SPEC.loader.exec_module(managed_tool_gateway)
is_managed_tool_gateway_ready = managed_tool_gateway.is_managed_tool_gateway_ready
resolve_managed_tool_gateway = managed_tool_gateway.resolve_managed_tool_gateway


def test_resolve_managed_tool_gateway_is_none_without_an_explicit_override():
    # No default managed gateway: without an explicit {VENDOR}_GATEWAY_URL there
    # is nowhere to route a vendor call, even with a token reader.
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FIRECRAWL_GATEWAY_URL", None)
        assert resolve_managed_tool_gateway("firecrawl", token_reader=lambda: "sk-thor-x") is None
        assert resolve_managed_tool_gateway("fal-queue") is None
        assert is_managed_tool_gateway_ready("modal") is False
        assert managed_tool_gateway.resolve_free_search_gateway(token_reader=lambda: "sk-thor-x") is None


def test_resolve_managed_tool_gateway_honors_an_explicit_override():
    with patch.dict(os.environ, {"FIRECRAWL_GATEWAY_URL": "http://127.0.0.1:3009/"}, clear=False):
        cfg = resolve_managed_tool_gateway("firecrawl", token_reader=lambda: "sk-thor-x")
        assert cfg is not None
        assert cfg.gateway_origin == "http://127.0.0.1:3009"
        assert cfg.api_key == "sk-thor-x"
        assert is_managed_tool_gateway_ready("firecrawl", token_reader=lambda: "sk-thor-x") is True


def test_build_vendor_gateway_url_honors_explicit_override_only():
    with patch.dict(os.environ, {"FIRECRAWL_GATEWAY_URL": "http://127.0.0.1:3009/"}, clear=False):
        assert managed_tool_gateway.build_vendor_gateway_url("firecrawl") == "http://127.0.0.1:3009"
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FIRECRAWL_GATEWAY_URL", None)
        assert managed_tool_gateway.build_vendor_gateway_url("firecrawl") == ""


def test_thorhub_api_key_readers_use_the_static_key(tmp_path, monkeypatch):
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-test")
    assert managed_tool_gateway.peek_thorhub_api_key() == "sk-thor-test"
    assert managed_tool_gateway.read_thorhub_api_key() == "sk-thor-test"
    monkeypatch.delenv("THORHUB_API_KEY")
    assert managed_tool_gateway.peek_thorhub_api_key() is None
    assert managed_tool_gateway.read_thorhub_api_key() is None


def test_connector_gateway_origin_is_empty_without_an_override():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("CONNECTOR_GATEWAY_URL", None)
        assert managed_gateway_auth.connector_gateway_origin() == ""


def test_connector_gateway_origin_honors_its_own_override():
    with patch.dict(os.environ, {"CONNECTOR_GATEWAY_URL": "http://127.0.0.1:3009/"}, clear=False):
        assert managed_gateway_auth.connector_gateway_origin() == "http://127.0.0.1:3009"
        assert managed_gateway_auth.is_managed_thorhub_gateway_url(
            "http://127.0.0.1:3009/v1/connectors/search"
        )


def test_bearer_gate_trusts_only_an_explicitly_configured_origin():
    # TOOL_GATEWAY_URL pins the media origin (the e2e harness sets it to a
    # loopback gateway), and the bearer gate must accept exactly that origin.
    with patch.dict(os.environ, {"TOOL_GATEWAY_URL": "http://127.0.0.1:3009/"}, clear=False):
        os.environ.pop("CONNECTOR_GATEWAY_URL", None)
        assert managed_gateway_auth.build_vendor_gateway_url("tool") == "http://127.0.0.1:3009"
        assert managed_gateway_auth.is_managed_thorhub_gateway_url(
            "http://127.0.0.1:3009/api/vendorx/generations"
        )
        assert not managed_gateway_auth.is_managed_thorhub_gateway_url(
            "https://tool-gateway.thor-agent.local/api/vendorx/generations"
        )
        assert not managed_gateway_auth.is_managed_thorhub_gateway_url(
            "http://127.0.0.1:3009.attacker.dev/api/vendorx/generations"
        )


def test_bearer_gate_trusts_nothing_by_default():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TOOL_GATEWAY_URL", None)
        os.environ.pop("CONNECTOR_GATEWAY_URL", None)
        for untrusted in (
            "https://connector-gateway.thor-agent.local/v1/connectors/execute",
            "https://tool-gateway.thor-agent.local/api/vendorx/generations",
            "http://connector-gateway.thor-agent.local/v1/connectors",
        ):
            assert not managed_gateway_auth.is_managed_thorhub_gateway_url(untrusted)
        assert managed_gateway_auth.managed_gateway_auth_headers("https://example.invalid/v1") == {}


def test_auth_headers_attach_the_thorhub_key_on_a_configured_origin(monkeypatch):
    monkeypatch.setenv("TOOL_GATEWAY_URL", "http://127.0.0.1:3009/")
    monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-test")
    headers = managed_gateway_auth.managed_gateway_auth_headers(
        "http://127.0.0.1:3009/api/vendorx/generations")
    assert headers["Authorization"] == "Bearer sk-thor-test"
    assert headers["User-Agent"].startswith("thor-agent/")


def test_read_thorhub_provider_state_falls_back_to_global_root_for_share_auth_profiles(tmp_path, monkeypatch):
    # A profile created with ``share_auth`` has no auth.json of its own; it signs in with the
    # root identity. The connector gate must see that identity, or manage_connections vanishes
    # from the profile's tool list while every other credential reader still works.
    root = tmp_path / ".thor"
    profile = root / "profiles" / "work"
    profile.mkdir(parents=True)
    (root / "auth.json").write_text(json.dumps({
        "version": 1,
        "providers": {"thor": {"auth_type": "api_key", "api_key": "sk-thor-x"}},
    }))
    monkeypatch.setenv("THOR_HOME", str(profile))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    import thor_constants
    from thor_cli import auth as auth_mod

    monkeypatch.setattr(thor_constants, "get_default_thor_root", lambda: root)
    monkeypatch.setattr(auth_mod, "get_thor_home", lambda: profile)
    monkeypatch.setattr(auth_mod, "_global_auth_store_cache", None)
    monkeypatch.setattr(auth_mod, "_auth_file_path", lambda: profile / "auth.json")

    state = managed_tool_gateway._read_thorhub_provider_state()

    assert state is not None
    assert state["auth_type"] == "api_key"
