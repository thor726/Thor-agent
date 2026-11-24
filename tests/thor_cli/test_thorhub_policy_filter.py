"""Narrowing model lists to an org's policy.

ThorHub has no org policy, so :func:`thorhub_policy_allowed_ids` always returns
``None`` (do not filter) and :func:`thorhub_policy_present` is always unknown.
The pure narrowing helper :func:`restrict_to_thorhub_policy` keeps its contract
for any allowlist a caller supplies.
"""

from __future__ import annotations

import base64
import json

import pytest

from thor_cli import models_pricing
import thor_cli.thorhub_account as account_mod
from thor_cli.models_pricing import _THORHUB_POLICY_APPEND_MAX, thorhub_policy_allowed_ids, restrict_to_thorhub_policy
from thor_cli.thorhub_account import thorhub_policy_present


def _jwt(claims: dict) -> str:
    def seg(obj):
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{seg({'alg': 'RS256'})}.{seg(claims)}.sig"


class TestRestrictToThorhubPolicy:
    def test_none_leaves_the_list_untouched(self):
        ids = ["a/one", "b/two"]
        assert restrict_to_thorhub_policy(ids, None) == ids

    def test_empty_set_leaves_the_list_untouched(self):
        """Empty is a failed read, not an org that may reach nothing."""
        ids = ["a/one", "b/two"]
        assert restrict_to_thorhub_policy(ids, set()) == ids

    def test_drops_ids_outside_the_policy(self):
        assert restrict_to_thorhub_policy(
            ["a/one", "b/two", "c/three"], {"a/one", "c/three"}
        ) == ["a/one", "c/three"]

    def test_preserves_curated_order(self):
        curated = ["z/last", "a/first", "m/middle"]
        allowed = {"a/first", "m/middle", "z/last"}
        assert restrict_to_thorhub_policy(curated, allowed) == curated

    def test_keeps_a_free_sibling_when_its_base_is_reachable(self):
        """ThorHub free picks would be ``:free`` ids."""
        assert restrict_to_thorhub_policy(["vendor/model:free"], {"vendor/model"}) == [
            "vendor/model:free"
        ]

    def test_keeps_a_free_id_listed_in_its_own_right(self):
        assert restrict_to_thorhub_policy(
            ["vendor/model:free"], {"vendor/model:free"}
        ) == ["vendor/model:free"]

    def test_drops_a_free_sibling_whose_base_is_blocked(self):
        assert restrict_to_thorhub_policy(["vendor/model:free"], {"other/model"}) == []


class TestThorhubPolicyAllowedIds:
    """ThorHub has no org policy: the allowlist is always None and no catalog read happens."""

    def test_always_none(self, monkeypatch):
        def _boom(*a, **kw):
            raise AssertionError("ThorHub must not fetch a catalog for a policy")

        monkeypatch.setattr(models_pricing, "fetch_models_with_pricing", _boom)
        assert thorhub_policy_allowed_ids() is None

    def test_always_none_even_when_a_policy_claim_is_patched(self, monkeypatch):
        monkeypatch.setattr(account_mod, "thorhub_policy_present", lambda: True)
        assert thorhub_policy_allowed_ids() is None


class TestThorhubPolicyPresent:
    """ThorHub has no org policy: always unknown (None), whatever token is presented."""

    def _patch_token(self, monkeypatch, token):
        import thor_cli.auth as auth_mod

        monkeypatch.setattr(
            auth_mod,
            "get_provider_auth_state",
            lambda _p: {"access_token": token} if token is not None else {},
        )

    @pytest.mark.parametrize("claim", [True, False])
    def test_jwt_claims_are_ignored(self, monkeypatch, claim):
        self._patch_token(monkeypatch, _jwt({"policy_present": claim}))
        assert thorhub_policy_present() is None

    def test_absent_claim_is_unknown(self, monkeypatch):
        self._patch_token(monkeypatch, _jwt({"org_id": "org_1"}))
        assert thorhub_policy_present() is None

    def test_non_boolean_claim_is_unknown(self, monkeypatch):
        self._patch_token(monkeypatch, _jwt({"policy_present": "yes"}))
        assert thorhub_policy_present() is None

    def test_no_token_is_unknown(self, monkeypatch):
        self._patch_token(monkeypatch, None)
        assert thorhub_policy_present() is None

    def test_undecodable_token_is_unknown(self, monkeypatch):
        self._patch_token(monkeypatch, "not-a-jwt")
        assert thorhub_policy_present() is None


class TestThorhubPolicyNotice:
    """No policy on ThorHub, so the notice is always silent."""

    def test_silent_when_a_policy_is_patched_present(self, monkeypatch):
        # The notice helper itself still renders when a policy is present (generic
        # helper contract); ThorHub never has one, so in practice it is silent.
        monkeypatch.setattr(account_mod, "thorhub_policy_present", lambda: True)
        assert account_mod.thorhub_policy_notice(removed=True) != ""

    def test_silent_otherwise(self, monkeypatch):
        for present in (False, None):
            monkeypatch.setattr(account_mod, "thorhub_policy_present", lambda: present)
            assert account_mod.thorhub_policy_notice(removed=True) == ""

    def test_silent_when_the_filter_removed_nothing(self, monkeypatch):
        monkeypatch.setattr(account_mod, "thorhub_policy_present", lambda: True)
        assert account_mod.thorhub_policy_notice(removed=False) == ""


class TestAllowlistOutsideTheCuratedList:
    """An allowlist can name only models the curated manifest lacks, which
    intersecting alone turns into an empty picker."""

    def test_surfaces_an_allowed_model_the_curated_list_lacks(self):
        assert restrict_to_thorhub_policy(
            ["vendor/a", "vendor/b"], {"amazon/nova-2-lite-v1"}, rescue_empty=True
        ) == ["amazon/nova-2-lite-v1"]

    def test_does_not_append_when_the_curated_overlap_is_non_empty(self):
        kept = restrict_to_thorhub_policy(
            ["z/curated", "a/curated"],
            {"z/curated", "a/curated", "new/model"},
            rescue_empty=True,
        )
        assert kept == ["z/curated", "a/curated"]

    def test_does_not_rescue_a_catalog_sized_allowed_set(self):
        """Past the cap the set reads as a whole catalog, and dumping it would
        bury the curated order the pickers show on purpose."""
        oversized = {f"cn/model-{i}" for i in range(_THORHUB_POLICY_APPEND_MAX + 1)}
        assert restrict_to_thorhub_policy(["vendor/one"], oversized, rescue_empty=True) == []


class TestRescueIsOptIn:
    """The rescue is meaningful only for the list a user picks from."""


    def test_an_already_empty_unavailable_list_is_never_filled(self):
        """A paid tier has no gated models, so this list is legitimately
        empty — not a filter result to rescue."""
        reachable = {f"cn/model-{i}" for i in range(42)}
        assert restrict_to_thorhub_policy([], reachable) == []


class TestPolicyRunsBeforeTierSplit:
    """A rescued id must still pass the free/paid predicate.

    Rescuing after the tier split put paid models back into a free-tier user's
    selectable list, and the same id into both lists at once.
    """

    def test_a_rescued_paid_model_stays_unavailable_for_a_free_tier_user(self):
        from thor_cli.models import partition_thorhub_models_by_tier

        pricing = {
            "vendor/free": {"prompt": "0", "completion": "0"},
            "vendor/paid": {"prompt": "0.000002", "completion": "0.00001"},
        }
        narrowed = restrict_to_thorhub_policy(
            list(pricing), {"vendor/paid"}, rescue_empty=True
        )
        selectable, unavailable = partition_thorhub_models_by_tier(
            narrowed, pricing, free_tier=True
        )

        assert selectable == []
        assert unavailable == ["vendor/paid"]
