"""Regression tests for the ThorHub static-key provider (Fase 4).

Replaces ``test_auth_nous_provider.py``: the Nous OAuth provider is retired, so the
provider tests cover the ThorHub static key — registry row, runtime credentials,
local auth status, session validity, model fetch, persist — plus the retired
guest surface (handoff / welcome trial / anonymous sign-in stubs). The TLS
``_resolve_verify`` classes are provider-agnostic and kept verbatim.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

from thor_cli.auth import AuthError


# =============================================================================
# _resolve_verify: CA bundle path validation
# =============================================================================


class TestResolveVerifyFallback:
    """Verify _resolve_verify falls back to default trust when the CA bundle
    path doesn't exist."""

    def test_missing_ca_bundle_in_auth_state_falls_back(self):
        import ssl
        from thor_cli.auth import _resolve_verify

        result = _resolve_verify(auth_state={
            "tls": {"insecure": False, "ca_bundle": "/nonexistent/ca-bundle.pem"},
        })
        # The subject is "falls back to _default_verify()", not the literal
        # True. Deriving the expectation from the real host keeps the
        # regression covered on the macOS lane too, where _default_verify
        # pins certifi's bundle and returns a context instead.
        if sys.platform == "darwin":
            assert isinstance(result, ssl.SSLContext)
        else:
            assert result is True

    def test_valid_ca_bundle_in_auth_state_is_returned(self, tmp_path):
        import ssl

        import certifi
        from truststore._ssl_constants import _original_SSLContext

        from thor_cli.auth import _resolve_verify

        result = _resolve_verify(auth_state={
            "tls": {"insecure": False, "ca_bundle": certifi.where()},
        })

        # An explicitly pinned bundle must NOT come back as a truststore
        # context — that would silently verify against the machine's store
        # instead of the bundle the connection asked for.
        assert isinstance(result, _original_SSLContext), (
            f"Expected the pinned-bundle context but got {type(result).__name__}: {result!r}"
        )
        assert not type(result).__module__.startswith("truststore")
        assert result.verify_mode == ssl.CERT_REQUIRED

    def test_insecure_takes_precedence_over_missing_ca(self):
        from thor_cli.auth import _resolve_verify

        result = _resolve_verify(
            insecure=True,
            auth_state={"tls": {"ca_bundle": "/nonexistent/ca.pem"}},
        )
        assert result is False

    def test_string_false_in_auth_state_does_not_disable_tls_verify(self):
        import ssl
        from thor_cli.auth import _resolve_verify

        result = _resolve_verify(auth_state={"tls": {"insecure": "false"}})
        assert result is not False
        assert result is True or isinstance(result, ssl.SSLContext)

    def test_string_true_in_auth_state_disables_tls_verify(self):
        from thor_cli.auth import _resolve_verify

        result = _resolve_verify(auth_state={"tls": {"insecure": "true"}})
        assert result is False


class TestDefaultVerifyAfterAnInstallRotation:
    """An OAuth credential exchange can be the first TLS client a long-lived gateway builds
    after the package manager replaced the environment certifi was imported from (#137255).

    It must never hand httpx a bundle path that no longer exists.
    """

    @pytest.mark.platforms("macos")
    def test_credential_verify_re_derives_the_rotated_bundle(self, tmp_path, monkeypatch):
        import ssl

        from thor_cli.auth import _resolve_verify

        for var in ("THOR_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            monkeypatch.delenv(var, raising=False)
        from tests.agent.test_ssl_verify import _rotated_certifi

        _rotated_certifi(tmp_path, monkeypatch, replacement=True)

        verify = _resolve_verify(auth_state={"tls": {"insecure": False}})

        # Nothing in the process points at the deleted environment, and httpx builds a client.
        import certifi

        assert Path(certifi.where()).is_file()
        with httpx.Client(verify=verify) as client:
            from typing import Any, cast

            transport = cast(Any, client._transport)
            assert transport._pool._ssl_context.verify_mode == ssl.CERT_REQUIRED


# =============================================================================
# ThorHub provider: registry, runtime credentials, status
# =============================================================================


@pytest.fixture
def thor_home(tmp_path, monkeypatch):
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    monkeypatch.delenv("THORHUB_API_KEY", raising=False)
    monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
    monkeypatch.delenv("NOUS_INFERENCE_BASE_URL", raising=False)
    return tmp_path


def _write_auth_json(thor_home: Path, providers: dict) -> None:
    thor_home.mkdir(parents=True, exist_ok=True)
    (thor_home / "auth.json").write_text(json.dumps({
        "version": 1, "active_provider": "thor", "providers": providers,
    }, indent=2))


class TestThorhubRegistry:
    def test_thor_row_is_api_key_with_thorhub_env(self):
        from thor_cli.auth import PROVIDER_REGISTRY

        row = PROVIDER_REGISTRY["thor"]
        assert row.auth_type == "api_key"
        assert row.name == "ThorHub"
        assert "THORHUB_API_KEY" in (row.api_key_env_vars or ())
        assert row.inference_base_url == "https://llm.thormarket.site/v1"
        assert row.portal_base_url == "https://llm.thormarket.site"

    def test_nous_is_not_a_registry_provider(self):
        from thor_cli.auth import PROVIDER_REGISTRY

        assert "nous" not in PROVIDER_REGISTRY

    def test_get_auth_status_thor_is_the_api_key_status(self, thor_home, monkeypatch):
        from thor_cli.auth import get_auth_status

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        status = get_auth_status("thor")
        assert status["logged_in"] is True
        assert status["provider"] == "thor"


class TestResolveThorhubRuntimeCredentials:
    def test_env_key_resolves(self, thor_home, monkeypatch):
        from thor_cli.auth_thorhub import resolve_thorhub_runtime_credentials

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-env")
        creds = resolve_thorhub_runtime_credentials()
        assert creds["provider"] == "thor"
        assert creds["api_key"] == "sk-thor-env"
        assert creds["base_url"] == "https://llm.thormarket.site/v1"
        assert creds["source"] == "thorhub_key"
        assert creds["key_id"] is None and creds["expires_at"] is None

    def test_missing_key_raises_actionable_auth_error(self, thor_home):
        from thor_cli.auth_thorhub import resolve_thorhub_runtime_credentials

        with pytest.raises(AuthError) as excinfo:
            resolve_thorhub_runtime_credentials()
        assert excinfo.value.code == "thorhub_auth_missing"
        assert "thor auth add thor" in str(excinfo.value)

    def test_singleton_key_resolves(self, thor_home):
        from thor_cli.auth_thorhub import resolve_thorhub_runtime_credentials

        _write_auth_json(thor_home, {"thor": {"api_key": "sk-thor-store"}})
        creds = resolve_thorhub_runtime_credentials()
        assert creds["api_key"] == "sk-thor-store"
        assert creds["source"] == "thorhub_key"

    def test_base_url_env_override_is_honored(self, thor_home, monkeypatch):
        from thor_cli.auth_thorhub import resolve_thorhub_runtime_credentials

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        monkeypatch.setenv("THORHUB_BASE_URL", "https://staging.thormarket.site")
        creds = resolve_thorhub_runtime_credentials()
        assert creds["base_url"] == "https://staging.thormarket.site/v1"

    def test_access_token_returns_the_key(self, thor_home, monkeypatch):
        from thor_cli.auth_thorhub import resolve_thorhub_access_token

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        assert resolve_thorhub_access_token() == "sk-thor-x"

    def test_access_token_missing_raises(self, thor_home):
        from thor_cli.auth_thorhub import resolve_thorhub_access_token

        with pytest.raises(AuthError) as excinfo:
            resolve_thorhub_access_token()
        assert excinfo.value.code == "thorhub_auth_missing"


class TestThorhubAuthStatusLocal:
    def test_no_key_is_not_logged_in(self, thor_home):
        from thor_cli.auth_thorhub import get_thorhub_auth_status_local

        status = get_thorhub_auth_status_local()
        assert status["logged_in"] is False
        assert status["provider"] == "thor"
        assert status["source"] == "none"
        assert status["inference_credential_present"] is False

    def test_env_key_is_logged_in(self, thor_home, monkeypatch):
        from thor_cli.auth_thorhub import get_thorhub_auth_status_local

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        status = get_thorhub_auth_status_local()
        assert status["logged_in"] is True
        assert status["source"] == "api_key"
        assert status["has_api_key"] is True
        assert status["inference_credential_present"] is True
        assert status["portal_base_url"] == "https://llm.thormarket.site"
        assert "sk-thor-x" not in json.dumps(status)

    def test_session_validity_is_valid_with_a_key_and_unknown_without(self, thor_home, monkeypatch):
        from thor_cli.auth_thorhub import get_thorhub_session_validity

        assert get_thorhub_session_validity() == "unknown"
        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        assert get_thorhub_session_validity() == "valid"


class TestPersistThorhubCredentials:
    def test_persist_writes_the_thor_singleton(self, thor_home):
        from thor_cli.auth import get_provider_auth_state
        from thor_cli.auth_thorhub import persist_thorhub_credentials

        persist_thorhub_credentials({"api_key": "sk-thor-new"})
        assert get_provider_auth_state("thor")["api_key"] == "sk-thor-new"

    def test_persist_twice_does_not_duplicate(self, thor_home):
        from thor_cli.auth import get_provider_auth_state
        from thor_cli.auth_thorhub import persist_thorhub_credentials

        persist_thorhub_credentials({"api_key": "sk-thor-new"})
        persist_thorhub_credentials({"api_key": "sk-thor-new"})
        state = get_provider_auth_state("thor")
        assert state["api_key"] == "sk-thor-new"
        assert "nous" not in (json.loads((thor_home / "auth.json").read_text())["providers"])

    def test_a_legacy_connectors_token_entitles_nothing(self, thor_home):
        # A leftover guest connectors token in a legacy "nous" provider state
        # (which only ever authorized vendor-tool calls) is not a ThorHub key.
        from thor_cli.thorhub_account import get_thorhub_account_info

        _write_auth_json(thor_home, {"nous": {
            "connectors_token": {"access_token": "guest-connectors-token", "expires_at": "2030-01-01T00:00:00+00:00"},
        }})
        info = get_thorhub_account_info()
        assert info.logged_in is False
        assert info.source == "none"


    def test_persist_without_a_key_raises(self, thor_home):
        from thor_cli.auth_thorhub import persist_thorhub_credentials

        with pytest.raises(AuthError):
            persist_thorhub_credentials({})


class TestFetchThorhubModels:
    def test_models_are_sorted_unique(self, monkeypatch, tmp_path):
        from thor_cli.auth_thorhub import fetch_thorhub_models
        from thor_cli.config import invalidate_env_cache

        # Hermetic default: no override anywhere. (The gateway multiplex tests leave
        # a profile .env memo behind that a bare default-resolution read would pick up.)
        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
        monkeypatch.delenv("NOUS_INFERENCE_BASE_URL", raising=False)
        invalidate_env_cache()

        def handler(request):
            assert str(request.url) == "https://llm.thormarket.site/v1/models"
            assert request.headers["authorization"] == "Bearer sk-thor-x"
            return httpx.Response(200, json={"data": [{"id": "b"}, {"id": "a"}, {"id": "a"}]})

        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
            transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"}))
        assert fetch_thorhub_models(api_key="sk-thor-x") == ["a", "b"]

    def test_base_url_with_v1_suffix_is_not_doubled(self, monkeypatch):
        from thor_cli.auth_thorhub import fetch_thorhub_models

        seen = []

        def handler(request):
            seen.append(str(request.url))
            return httpx.Response(200, json={"data": []})

        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
            transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"}))
        fetch_thorhub_models(inference_base_url="https://llm.thormarket.site/v1", api_key="sk-thor-x")
        assert seen == ["https://llm.thormarket.site/v1/models"]

    def test_non_200_raises_models_fetch_failed(self, monkeypatch):
        from thor_cli.auth_thorhub import fetch_thorhub_models

        def handler(request):
            return httpx.Response(401, json={"error": "unauthorized"})

        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
            transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"}))
        with pytest.raises(AuthError) as excinfo:
            fetch_thorhub_models(api_key="sk-thor-x")
        assert excinfo.value.code == "models_fetch_failed"


# =============================================================================
# Retired guest surface: stubs answer honestly, never mint
# =============================================================================


class TestRetiredGuestSurface:
    def test_handoff_drain_is_empty_and_wire_status_is_none(self):
        from thor_cli.guest_handoff import drain, wire_status

        assert drain() == []
        assert wire_status(None) == {"status": "none", "updated_at": None}

    def test_welcome_trial_claim_is_always_blocked(self):
        from thor_cli.welcome_trial import claim_blocker

        assert "retired" in claim_blocker()

    def test_anon_sign_in_fails_without_a_key_and_reports_signed_in_with_one(
        self, thor_home, monkeypatch,
    ):
        from thor_cli.anon_sign_in import run_sign_in

        states = list(run_sign_in())
        assert len(states) == 1
        assert states[0].kind == "failed"
        assert states[0].reason == "thorhub_no_free_tier"

        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        states = list(run_sign_in())
        assert len(states) == 1
        assert states[0].kind == "already_signed_in"

    def test_device_auth_timeout_message_defaults_to_thorhub(self):
        from thor_cli.auth_device_flow import _device_auth_timeout_message

        assert "https://llm.thormarket.site" in _device_auth_timeout_message("")
