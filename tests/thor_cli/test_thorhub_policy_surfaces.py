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


class TestThorhubLiveListMatchesDocs:
    """Fix #3: ThorHub picker + validation follow the live list (docs).

    The gateway bills an unregistered model id back as an abuse penalty, so the
    picker shows only the models the gateway actually serves (the active ones,
    exactly the list at llm.thormarket.site/docs) and switching to an id outside
    the live list is rejected, never soft-accepted from the curated catalog.
    """

    # Representative live /v1/models listing: active ids + one registered but
    # disabled id (in the listing, so the gateway will not penalise it).
    LIVE = ["auto", "deepseek-v4-flash", "deepseek-v4-pro", "claude-opus-5"]
    BAD_CURATED = "deepseek/deepseek-v4.1-flash"
    THORHUB_URL = "https://llm.thormarket.site/v1"

    @pytest.fixture(autouse=True)
    def _live_listing(self, monkeypatch):
        monkeypatch.setattr(
            "thor_cli.models.fetch_api_models", lambda *a, **k: list(self.LIVE))
        monkeypatch.setattr(
            "thor_cli.models.probe_api_models",
            lambda *a, **k: {
                "models": list(self.LIVE),
                "probed_url": self.THORHUB_URL + "/models",
                "resolved_base_url": self.THORHUB_URL,
                "used_fallback": False,
            })
        yield

    # --- Fix A: validation rejects ids outside the live ThorHub list ---
    def test_thorhub_rejects_curated_id_not_in_live_list(self):
        from thor_cli.models_validate import validate_requested_model

        result = validate_requested_model(
            self.BAD_CURATED, "thor", api_key="sk-thor-x", base_url=self.THORHUB_URL)
        assert result["accepted"] is False
        assert "live" in (result["message"] or "").lower()

    def test_thorhub_accepts_live_active_id(self):
        from thor_cli.models_validate import validate_requested_model

        result = validate_requested_model(
            "deepseek-v4-flash", "thor", api_key="sk-thor-x", base_url=self.THORHUB_URL)
        assert result["accepted"] is True

    def test_thorhub_accepts_registered_but_disabled_id(self):
        # In the live listing, so the gateway will not penalise it (it fails with
        # model_disabled instead). Validation only guards the penalty boundary.
        from thor_cli.models_validate import validate_requested_model

        result = validate_requested_model(
            "claude-opus-5", "thor", api_key="sk-thor-x", base_url=self.THORHUB_URL)
        assert result["accepted"] is True

    def test_custom_thorhub_endpoint_rejects_curated_id(self):
        from thor_cli.models_validate import validate_requested_model

        result = validate_requested_model(
            self.BAD_CURATED, "custom", api_key="sk-thor-x", base_url=self.THORHUB_URL)
        assert result["accepted"] is False

    def test_other_provider_still_soft_accepts_curated_id(self):
        # Other providers keep the old behaviour: a curated id missing from the
        # live listing is accepted with a note (their listings omit valid models).
        from thor_cli.models import OPENROUTER_MODELS
        from thor_cli.models_validate import validate_requested_model

        curated_id = next(mid for mid, _ in OPENROUTER_MODELS if mid not in self.LIVE)
        result = validate_requested_model(curated_id, "openrouter", api_key="sk-or-x")
        assert result["accepted"] is True

    # --- Fix B: only active models come back from the ThorHub fetch ---
    def test_fetch_returns_only_active_models(self, monkeypatch):
        import thor_cli.auth_thorhub as ah

        payload = {"data": [
            {"id": "auto", "enabled": True, "available": True},
            {"id": "deepseek-v4-pro", "enabled": True, "available": True},
            {"id": "claude-opus-5", "enabled": False, "available": False},
            {"id": "glm-5", "enabled": True, "available": False},
            {"id": "legacy-model"},
        ]}

        class _Resp:
            status_code = 200

            def json(self):
                return payload

        class _Client:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, url, headers=None):
                return _Resp()

        monkeypatch.setattr(ah, "_thorhub_http_client", lambda *a, **k: _Client())
        monkeypatch.setattr("thor_cli.thorhub_account.thorhub_api_key", lambda: "sk-thor-x")
        monkeypatch.setattr(
            "thor_cli.thorhub_account.resolve_thorhub_base_url",
            lambda: self.THORHUB_URL)
        assert ah.fetch_thorhub_models() == ["auto", "deepseek-v4-pro", "legacy-model"]

    # --- Fix C: non-blocking picker reads the cached live list ---
    def test_non_blocking_picker_reads_live_cache(self, monkeypatch, tmp_path):
        import thor_cli.model_switch_providers as msp

        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        assert msp._live_thorhub_model_ids(non_blocking=True) == []
        msp._write_thorhub_models_cache(["auto", "deepseek-v4-flash"])
        assert msp._live_thorhub_model_ids(non_blocking=True) == ["auto", "deepseek-v4-flash"]

    def test_stale_cache_is_ignored(self, monkeypatch, tmp_path):
        import json
        import time

        import thor_cli.model_switch_providers as msp

        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        cache_path = msp._thorhub_models_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "fetched_at": time.time() - 25 * 60 * 60,
            "models": ["auto", "deepseek-v4-flash"],
        }), encoding="utf-8")
        assert msp._live_thorhub_model_ids(non_blocking=True) == []

    def test_blocking_fetch_writes_cache(self, monkeypatch, tmp_path):
        import thor_cli.auth_thorhub as ah
        import thor_cli.model_switch_providers as msp

        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        monkeypatch.setattr(
            ah, "fetch_thorhub_models", lambda **k: ["auto", "deepseek-v4-flash"])
        assert msp._live_thorhub_model_ids() == ["auto", "deepseek-v4-flash"]
        assert msp._live_thorhub_model_ids(non_blocking=True) == ["auto", "deepseek-v4-flash"]

    # --- Fix #4: the picker catalog itself is the live list, not the curated manifest ---
    def test_thorhub_catalog_returns_live_active_models(self, monkeypatch):
        # The /model picker reads its Thor row through provider_model_ids ->
        # _thorhub_catalog; that fetcher used to return the curated manifest, so a
        # fresh reinstall still showed vendor-prefixed ids (deepseek/..., z-ai/...)
        # that validation then rejected. It must return the live list instead.
        import thor_cli.auth_thorhub as ah
        from thor_cli.models import _thorhub_catalog

        monkeypatch.setattr(
            ah, "fetch_thorhub_models", lambda **k: ["auto", "deepseek-v4-flash"])
        assert _thorhub_catalog("thor", False) == ["auto", "deepseek-v4-flash"]

    def test_thorhub_catalog_falls_back_when_fetch_fails(self, monkeypatch):
        # No key / gateway down: None, so the caller falls through to the curated
        # manifest instead of an empty picker.
        import thor_cli.auth_thorhub as ah
        from thor_cli.models import _thorhub_catalog

        def _raise(**kwargs):
            raise RuntimeError("ThorHub key not configured")

        monkeypatch.setattr(ah, "fetch_thorhub_models", _raise)
        assert _thorhub_catalog("thor", False) is None

    def test_thorhub_catalog_falls_back_when_fetch_empty(self, monkeypatch):
        import thor_cli.auth_thorhub as ah
        from thor_cli.models import _thorhub_catalog

        monkeypatch.setattr(ah, "fetch_thorhub_models", lambda **k: [])
        assert _thorhub_catalog("thor", False) is None
