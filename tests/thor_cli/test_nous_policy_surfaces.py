"""Every ThorHub model list is narrowed to the org's policy before it is shown.

Four surfaces build their list from the curated manifest unioned with the
ThorHub catalog; neither source is authenticated.
"""

from __future__ import annotations

import argparse

import pytest

import thor_cli.models as models_mod
from thor_cli import models_pricing

CURATED = ["vendor/allowed", "vendor/blocked"]
ALLOWED = {"vendor/allowed"}

@pytest.fixture
def policy(monkeypatch):
    """An org whose policy admits only ``vendor/allowed``."""
    monkeypatch.setattr(models_pricing, "thorhub_policy_allowed_ids", lambda **_k: ALLOWED)
    return ALLOWED

@pytest.fixture
def no_policy(monkeypatch):
    """An unrestricted org — lists must come through untouched."""
    monkeypatch.setattr(models_pricing, "thorhub_policy_allowed_ids", lambda **_k: None)

class TestLoginThorhub:

    def _run(self, monkeypatch, tmp_path, live=None):
        import thor_cli.auth as auth_mod
        import thor_cli.model_setup_flows as msf
        import thor_cli.model_switch_providers as msp
        import thor_cli.thorhub_subscription as ns

        seen: dict = {}
        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        monkeypatch.setenv("THORHUB_API_KEY", "sk-thor-x")
        monkeypatch.setattr(models_mod, "get_curated_thorhub_model_ids", lambda: list(CURATED))
        # The live gateway list is the picker's first choice; stub it so the
        # test never touches the network. Default [] keeps the old curated
        # behaviour for the policy tests below.
        monkeypatch.setattr(msp, "_live_thorhub_model_ids", lambda **kw: list(live or []))
        monkeypatch.setattr(models_pricing, "get_pricing_for_provider", lambda _p: {})
        monkeypatch.setattr(models_mod, "check_thorhub_free_tier", lambda **_k: None)
        monkeypatch.setattr(
            models_mod,
            "union_with_portal_paid_recommendations",
            lambda ids, pricing, _portal: (list(ids), pricing),
        )
        monkeypatch.setattr(ns, "prompt_enable_tool_gateway", lambda _c: None)

        def _capture(model_ids, **kwargs):
            seen["model_ids"] = list(model_ids)

        monkeypatch.setattr(auth_mod, "_prompt_model_selection", _capture)
        msf._model_flow_thorhub({}, "", None)
        return seen

    def test_hidden_model_is_not_offered(self, monkeypatch, tmp_path, policy):
        assert self._run(monkeypatch, tmp_path).get("model_ids") == ["vendor/allowed"]

    def test_unrestricted_org_sees_the_full_curated_list(
        self, monkeypatch, tmp_path, no_policy
    ):
        assert self._run(monkeypatch, tmp_path).get("model_ids") == CURATED

    def test_picker_shows_live_list_right_after_login(
        self, monkeypatch, tmp_path, no_policy
    ):
        """Right after entering the key, the buyer sees the gateway's live ids.

        A curated id the gateway does not serve triggers its penalty guard
        (a flat token charge on the buyer's key), so the live list must win
        over the curated snapshot whenever the fetch succeeds.
        """
        live = ["live/a", "live/b"]
        assert self._run(monkeypatch, tmp_path, live=live).get("model_ids") == live

    def test_picker_falls_back_to_curated_list_when_live_unavailable(
        self, monkeypatch, tmp_path, no_policy
    ):
        """Offline (live fetch fails): the curated list is the fallback."""
        assert self._run(monkeypatch, tmp_path, live=[]).get("model_ids") == CURATED

class TestModelSwitchPicker:
    """The ``/model`` picker's thor branch (``list_authenticated_providers``)."""

    def _rows(self, monkeypatch):
        import thor_cli.auth as auth_mod
        import thor_cli.model_switch as ms

        monkeypatch.setattr(
            auth_mod,
            "_load_auth_store",
            lambda *a, **k: {"providers": {"thor": {"api_key": "sk-thor-x"}}},
        )
        monkeypatch.setattr(models_mod, "get_curated_thorhub_model_ids", lambda: list(CURATED))
        monkeypatch.setattr(models_pricing, "get_pricing_for_provider", lambda _p: {})
        monkeypatch.setattr(models_mod, "check_thorhub_free_tier", lambda **_k: None)
        monkeypatch.setattr(
            models_mod,
            "union_with_portal_paid_recommendations",
            lambda ids, pricing, _portal: (list(ids), pricing),
        )
        rows = ms.list_authenticated_providers(max_models=10)
        return next((r for r in rows if r["slug"] == "thor"), None)

    def test_hidden_model_is_filtered(self, monkeypatch, policy):
        row = self._rows(monkeypatch)
        assert row is not None, "thor row should be listed"
        assert "vendor/blocked" not in row["models"]
        assert "vendor/allowed" in row["models"]

    def test_unrestricted_org_keeps_both(self, monkeypatch, no_policy):
        row = self._rows(monkeypatch)
        assert row is not None
        assert set(CURATED) <= set(row["models"])

    def test_filter_survives_a_failed_recommendation_fetch(self, monkeypatch, policy):
        """The filter sits outside the try wrapping the Portal union."""

        def _boom(_p):
            raise RuntimeError("portal down")

        monkeypatch.setattr(models_pricing, "get_pricing_for_provider", _boom)
        row = self._rows(monkeypatch)
        assert row is not None
        assert "vendor/blocked" not in row["models"]

class TestRecommendedDefaultEndpoint:
    """This endpoint picks a model the user never sees chosen."""

    def _call(self, monkeypatch):
        import thor_cli.auth as auth_mod
        from thor_cli.web_routers.models import get_recommended_default_model

        # Blocked first, so an unfiltered list would make it the silent
        # default — otherwise this passes whether or not the filter runs.
        monkeypatch.setattr(
            models_mod, "get_curated_thorhub_model_ids",
            lambda: ["vendor/blocked", "vendor/allowed"],
        )
        monkeypatch.setattr(models_pricing, "get_pricing_for_provider", lambda _p: {})
        monkeypatch.setattr(models_mod, "check_thorhub_free_tier", lambda **_k: None)
        monkeypatch.setattr(
            models_mod,
            "union_with_portal_paid_recommendations",
            lambda ids, pricing, _portal: (list(ids), pricing),
        )
        monkeypatch.setattr(auth_mod, "get_provider_auth_state", lambda _p: {})
        return get_recommended_default_model(provider="thor")

    def test_hidden_model_is_never_the_silent_default(self, monkeypatch, policy):
        assert self._call(monkeypatch)["model"] == "vendor/allowed"

    def test_unrestricted_org_is_unaffected(self, monkeypatch, no_policy):
        assert self._call(monkeypatch)["model"] == "vendor/blocked"

class TestAuxiliaryFastModel:
    """``_fast_model_from_catalog`` uses the catalog's keys as a source of ids."""

    def _pick(self, monkeypatch, *, catalog):
        import agent.auxiliary_client as aux

        seen: dict = {}

        def _fake_fetch(*, api_key=None, base_url="", timeout=8.0, **_k):
            seen["api_key"] = api_key
            return {mid: {} for mid in catalog}

        monkeypatch.setattr(
            models_pricing, "_resolve_thorhub_pricing_credentials",
            lambda: ("sk-thor", "https://inference.example.com"),
        )
        monkeypatch.setattr(models_pricing, "fetch_models_with_pricing", _fake_fetch)
        picked = aux._fast_model_from_catalog("thor")
        return picked, seen

    def test_hidden_model_is_not_selected(self, monkeypatch, policy):
        import agent.auxiliary_client as aux

        monkeypatch.setattr(
            models_pricing, "thorhub_policy_allowed_ids", lambda **_k: {"vendor/allowed"}
        )
        monkeypatch.setattr(aux, "_FAST_MODEL_FAMILIES", ("vendor/",))
        monkeypatch.setattr(aux, "_FAST_MODEL_EXCLUDE", ())
        picked, _ = self._pick(
            monkeypatch, catalog=["vendor/blocked", "vendor/allowed"]
        )
        assert picked == "vendor/allowed"

class TestThorhubPrefetch:
    """The thor disk-cache entry is write-only, so prefetching it is a round
    trip for nothing."""

class TestPolicyNoticeIsShown:

    def test_login_prints_it(self, monkeypatch, tmp_path, policy, capsys):
        import thor_cli.thorhub_account as account_mod

        monkeypatch.setattr(account_mod, "thorhub_policy_present", lambda: True)
        TestLoginThorhub()._run(monkeypatch, tmp_path)
        assert account_mod.thorhub_policy_notice(removed=True) in capsys.readouterr().out

class TestAuxFallbackRespectsPolicy:
    """Steps 2-4 of the aux ladder are policy-blind: `resolve_aux_model` queries
    a public recommendation and the rest are hardcoded."""

    def _patch(self, monkeypatch, *, allowed, recommended):
        import agent.auxiliary_client as aux
        import providers

        monkeypatch.setattr(models_pricing, "thorhub_policy_allowed_ids", lambda **_k: allowed)
        monkeypatch.setattr(
            models_pricing, "_resolve_thorhub_pricing_credentials",
            lambda: ("sk", "https://inference.example.com"),
        )
        # No fast-family match, so the catalog step yields nothing.
        monkeypatch.setattr(
            models_pricing, "fetch_models_with_pricing",
            lambda **_k: {"vendor/allowed-large": {}},
        )

        class _Profile:
            default_aux_model = ""

            def resolve_aux_model(self, **_k):
                return recommended

        monkeypatch.setattr(providers, "get_provider_profile", lambda _p: _Profile())
        return aux

    def test_blocked_recommendation_is_not_used(self, monkeypatch):
        aux = self._patch(
            monkeypatch, allowed={"vendor/allowed-large"},
            recommended="vendor/blocked-haiku",
        )
        assert aux._get_aux_model_for_provider("thor", prefer_fast=True) == ""

    def test_allowed_recommendation_still_used(self, monkeypatch):
        aux = self._patch(
            monkeypatch, allowed={"vendor/allowed-large", "vendor/ok-haiku"},
            recommended="vendor/ok-haiku",
        )
        assert (
            aux._get_aux_model_for_provider("thor", prefer_fast=True)
            == "vendor/ok-haiku"
        )

    def test_ungoverned_org_is_unaffected(self, monkeypatch):
        aux = self._patch(
            monkeypatch, allowed=None, recommended="vendor/anything"
        )
        assert (
            aux._get_aux_model_for_provider("thor", prefer_fast=True)
            == "vendor/anything"
        )
