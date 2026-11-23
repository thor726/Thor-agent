"""Regression tests for #29285 — provider precedence in resolve_provider("auto").

Explicit user intent (config.yaml model.provider, env-var API keys) must win
over a stale logged-in OAuth `active_provider` in auth.json. Before the fix,
`active_provider` sat above the env/config checks and silently overrode an
explicit choice — e.g. a user OAuth-logged-into Anthropic but with
OPENAI_API_KEY exported (or model.provider set) got routed to Anthropic.
"""
import pytest

from thor_cli.auth import resolve_provider, AuthError


def _login(monkeypatch, provider_id):
    """Simulate a logged-in OAuth active_provider in auth.json."""
    monkeypatch.setattr("thor_cli.auth._load_auth_store",
                        lambda: {"active_provider": provider_id})
    monkeypatch.setattr("thor_cli.auth.get_auth_status",
                        lambda p: {"logged_in": p == provider_id})


def _config(monkeypatch, model_cfg):
    monkeypatch.setattr("thor_cli.config.load_config", lambda: {"model": model_cfg})


def _no_aws(monkeypatch):
    # Neutralize any ambient AWS creds so Bedrock auto-detect can't interfere.
    monkeypatch.setattr("agent.bedrock_adapter.has_aws_credentials", lambda *_a, **_kw: False)


def _clear_provider_env(monkeypatch):
    for var in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GLM_API_KEY", "ZAI_API_KEY",
                "KIMI_API_KEY", "MINIMAX_API_KEY", "THOR_INFERENCE_PROVIDER"):
        monkeypatch.delenv(var, raising=False)


class TestProviderPrecedence:
    def test_config_provider_beats_stale_oauth(self, monkeypatch):
        """config.yaml model.provider wins over a logged-in OAuth active_provider."""
        _clear_provider_env(monkeypatch)
        _no_aws(monkeypatch)
        _login(monkeypatch, "anthropic")           # stale OAuth login
        _config(monkeypatch, {"provider": "zai", "default": "glm-4.6"})
        assert resolve_provider("auto") == "zai"

    def test_env_key_beats_stale_oauth(self, monkeypatch):
        """An exported provider API key wins over a logged-in OAuth active_provider."""
        _clear_provider_env(monkeypatch)
        _no_aws(monkeypatch)
        _login(monkeypatch, "anthropic")
        _config(monkeypatch, {"default": "some-model"})  # dict, NO provider key
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        assert resolve_provider("auto") == "openai-api"


    def test_oauth_used_as_last_resort(self, monkeypatch):
        """With NO config provider and NO env keys, the logged-in OAuth provider
        is still used (it's the last-resort fallback, not removed)."""
        _clear_provider_env(monkeypatch)
        _no_aws(monkeypatch)
        _login(monkeypatch, "anthropic")
        _config(monkeypatch, {})  # empty model config, no provider
        assert resolve_provider("auto") == "anthropic"




    def test_openrouter_pool_beats_stale_oauth(self, monkeypatch):
        """An OpenRouter credential-pool entry (no env var) wins over a logged-in
        OAuth provider — the pool rung sits above OAuth (#42130 + #29285)."""
        _clear_provider_env(monkeypatch)
        _no_aws(monkeypatch)
        _login(monkeypatch, "anthropic")
        _config(monkeypatch, {})

        class _Pool:
            def has_credentials(self):
                return True

        monkeypatch.setattr("agent.credential_pool.load_pool", lambda name: _Pool())
        assert resolve_provider("auto") == "openrouter"


@pytest.fixture
def portal(monkeypatch, tmp_path):
    from tests.thor_cli.anon_portal import install_portal
    return install_portal(monkeypatch, tmp_path)


def _never_mint(monkeypatch):
    """The resolver is a READ: any call into the creator from inside it is a bug."""
    monkeypatch.setattr("thor_cli.anon_auth.ensure_portal_identity",
                        lambda **kw: (_ for _ in ()).throw(AssertionError("resolve_provider must not mint")))


def _thorhub_key_with_aws(monkeypatch):
    """A ThorHub key in the env, then a leftover ~/.aws profile."""
    from tests.thor_cli.anon_portal import as_local_desktop_backend
    _clear_provider_env(monkeypatch)
    as_local_desktop_backend(monkeypatch)
    _never_mint(monkeypatch)
    monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-test")
    monkeypatch.setattr("agent.bedrock_adapter.has_aws_credentials", lambda *_a, **_kw: True)


class TestThorhubKeyBeatsImplicitHostCredentials:
    """NS-829 (ThorHub era): a leftover ~/.aws profile must not pre-empt a configured ThorHub key.

    A ThorHub key sits above the implicit Bedrock chain; explicit intent still beats it.
    The resolver never creates an identity. (There is no free tier anymore: the welcome
    trial and its ladder rung are retired with the Nous Portal.)
    """

    def test_a_thorhub_key_beats_the_bedrock_chain(self, monkeypatch):
        _thorhub_key_with_aws(monkeypatch)
        assert resolve_provider("auto") == "thor"

    def test_a_config_provider_beats_a_thorhub_key(self, monkeypatch):
        _thorhub_key_with_aws(monkeypatch)
        _config(monkeypatch, {"provider": "zai", "default": "some-model"})
        assert resolve_provider("auto") == "zai"

    def test_an_explicit_env_key_beats_the_bedrock_chain(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        _never_mint(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setattr("agent.bedrock_adapter.has_aws_credentials", lambda *_a, **_kw: True)
        assert resolve_provider("auto") == "openai-api"

    def test_skip_free_tier_still_resolves_a_thorhub_key(self, monkeypatch):
        """``skip_free_tier`` is accepted and ignored now: a ThorHub key is not a free tier."""
        _thorhub_key_with_aws(monkeypatch)
        assert resolve_provider("auto", skip_free_tier=True) == "thor"

    def test_without_a_key_the_ladder_falls_through_to_bedrock(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        _never_mint(monkeypatch)
        monkeypatch.setattr("agent.bedrock_adapter.has_aws_credentials", lambda *_a, **_kw: True)
        assert resolve_provider("auto") == "bedrock"
