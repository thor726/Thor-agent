"""Regression for #132728: registered ThorHub RPCs bind the selected profile.

Exercise real RPC registration, worker dispatch, and endpoint resolution against
two synthetic homes. Only external HTTP is substituted.

ThorHub shape: each home carries its own static ``sk-thor-...`` key plus its own
``THORHUB_BASE_URL`` override; the balance read (``GET {base}/portal/member/me``)
is the only HTTP the billing reads make, and every write is refused locally
(ThorHub has no billing API) without any request leaving.
"""

import io
import json
import logging
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest


def _home(home, label):
    home.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: thor\n  default: fixture-model\n")
    # THOR_PORTAL_BASE_URL is legacy, kept only for the step-up probe below:
    # auth.step_up_nous_billing_scope still reads it (Commit D rewrites that flow).
    (home / ".env").write_text(
        f"THORHUB_BASE_URL=https://{label}-portal.invalid\n"
        f"THOR_PORTAL_BASE_URL=https://{label}-portal.invalid\n")
    (home / "auth.json").write_text(json.dumps({"version": 1, "providers": {"thor": {
        "api_key": f"sk-thor-{label}",
    }}}))


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    launch = tmp_path / "launch-home"
    secondary = launch / "profiles" / "secondary"
    _home(launch, "launch")
    _home(secondary, "secondary")
    monkeypatch.setenv("THOR_HOME", str(launch))
    monkeypatch.setenv("THOR_SHARED_AUTH_DIR", str(tmp_path / "shared-auth"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    from agent import billing_usage, billing_view, secret_scope, subscription_view
    from thor_cli import auth, thorhub_account, thorhub_billing
    from tui_gateway import launch_profile_policy, server

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
    calls = []

    def urlopen(request, *args, **kwargs):
        calls.append((request.get_method(), request.full_url, request.get_header("Authorization")))
        response = io.BytesIO(json.dumps({"data": {
            "tokens_remaining": 5000, "token_limit": 10000, "tokens_used": 5000, "is_active": True,
        }}).encode())
        response.status = 200
        return response
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    try:
        yield SimpleNamespace(server=server, homes={"launch": launch, "secondary": secondary},
                              calls=calls)
    finally:
        secret_scope.set_multiplex_active(previous)


class Wire:
    def __init__(self):
        self.event = threading.Event()
        self.response = None

    def write(self, response):
        self.response = response
        self.event.set()
        return True


def _call(server, method, params):
    wire = Wire()
    response = server.dispatch({"jsonrpc": "2.0", "id": "probe", "method": method, "params": params}, wire)
    if response is None:
        assert wire.event.wait(10), "registered RPC did not return"
        response = wire.response
    assert "result" in response, response
    return response["result"]


@pytest.mark.parametrize("profile", ["launch", "secondary"])
def test_billing_state_reads_the_profiles_own_thorhub_balance(runtime, caplog, monkeypatch, profile):
    params = {} if profile == "launch" else {"profile": "secondary"}
    # A sibling's later ambient edit must not override the frozen launch scope or the selected profile.
    monkeypatch.setenv("THORHUB_BASE_URL", "https://ambient-other.invalid")
    ambient = dict(os.environ)
    with caplog.at_level(logging.WARNING):
        result = _call(runtime.server, "billing.state", params)
    assert result.get("logged_in") is True, result
    warnings = [r.getMessage() for r in caplog.records if "no profile secret scope" in r.getMessage()]
    assert not warnings, warnings
    assert runtime.calls
    assert all(url == f"https://{profile}-portal.invalid/portal/member/me"
               for _, url, _ in runtime.calls), runtime.calls
    assert all(auth == f"Bearer sk-thor-{profile}" for _, _, auth in runtime.calls), runtime.calls
    assert dict(os.environ) == ambient


@pytest.mark.parametrize("profile", ["launch", "secondary"])
def test_billing_state_keeps_profile_routing_when_switching_homes(runtime, caplog, profile):
    with caplog.at_level(logging.WARNING):
        for profile in ("launch", "secondary", "launch"):
            runtime.calls.clear()
            result = _call(runtime.server, "billing.state", {} if profile == "launch" else {"profile": profile})
            assert result.get("logged_in") is True, result
            assert runtime.calls, runtime.calls
            for verb, url, auth in runtime.calls:
                assert url == f"https://{profile}-portal.invalid/portal/member/me", runtime.calls
                assert auth == f"Bearer sk-thor-{profile}", runtime.calls
    assert not [r for r in caplog.records if "no profile secret scope" in r.getMessage()]


@pytest.mark.parametrize("profile", ["launch", "secondary"])
def test_subscription_state_is_static_thorhub_and_touches_no_portal(runtime, profile):
    # ThorHub has no subscriptions: the state is static (no plan, top-up deep-link)
    # and no HTTP leaves for any profile.
    result = _call(runtime.server, "subscription.state", {} if profile == "launch" else {"profile": profile})
    assert result.get("logged_in") is True, result
    assert runtime.calls == []


def test_usage_bars_is_unavailable_on_thorhub(runtime):
    # ThorHub has no dollar usage model (the balance lives on /topup).
    result = _call(runtime.server, "usage.bars", {})
    assert result.get("available") is False, result
    assert runtime.calls == []


@pytest.mark.parametrize("method,params", [
    ("subscription.preview", {"subscription_type_id": "fixture-tier"}),
    ("subscription.change", {"cancel": True}),
    ("subscription.resume", {}),
    ("subscription.upgrade", {"subscription_type_id": "fixture-tier"}),
    ("billing.charge", {"amount_usd": "1"}),
    ("billing.charge_status", {"charge_id": "fixture-charge"}),
    ("billing.auto_reload", {"threshold": "1", "top_up_amount": "1"}),
])
@pytest.mark.parametrize("profile", ["launch", "secondary"])
def test_sibling_writes_are_refused_without_touching_any_portal(runtime, caplog, method, params, profile):
    # ThorHub has no billing API: every write is refused locally with the top-up
    # deep-link, identically for both profiles, and no request ever leaves for
    # any profile's ThorHub host.
    with caplog.at_level(logging.WARNING):
        result = _call(runtime.server, method, params | ({} if profile == "launch" else {"profile": profile}))
    assert result["ok"] is False, result
    assert result["error"] == "thorhub_no_billing_api", result
    assert result["portal_url"] == "https://llm.thormarket.site/beli/topup", result
    assert runtime.calls == []
    assert not [r for r in caplog.records if "no profile secret scope" in r.getMessage()]


@pytest.mark.parametrize("profile", ["launch", "secondary"])
def test_step_up_binds_the_profile_before_starting_the_external_flow(runtime, monkeypatch, profile):
    from agent.secret_scope import get_secret
    from thor_cli import auth
    from thor_constants import get_thor_home

    seen = []
    def external_device_flow(**kwargs):
        seen.append((get_thor_home(), get_secret("THOR_PORTAL_BASE_URL")))
        return True
    monkeypatch.setattr(auth, "step_up_nous_billing_scope", external_device_flow)
    result = _call(runtime.server, "billing.step_up", {} if profile == "launch" else {"profile": profile})
    assert result == {"ok": True, "granted": True}, result
    assert seen == [(runtime.homes[profile], f"https://{profile}-portal.invalid")]


@pytest.mark.parametrize("method", ["billing.state", "subscription.state", "usage.bars"])
def test_missing_profile_fails_before_any_portal_request(runtime, method):
    wire = Wire()
    response = runtime.server.dispatch({"jsonrpc": "2.0", "id": "probe", "method": method,
                                       "params": {"profile": "missing"}}, wire)
    if response is None:
        assert wire.event.wait(10)
        response = wire.response
    assert response["error"]["code"] == 4064, response
    assert runtime.calls == []
