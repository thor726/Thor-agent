"""The ThorHub plane credential resolves under its own profile's secret scope when the gateway multiplexes.

The Remote Config poller is a bare thread with no profile scope. Without a binding, the resolver's
read of ``THORHUB_BASE_URL`` fails closed and the profile's own key is never found: a secondary's
key would be read from the wrong home, or the launch profile's env override would leak into a
secondary. The key is static — there is no refresh and no Portal allowlist anymore — so the
invariant under test is per-profile key resolution, not refresh routing.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import pytest

from agent.secret_scope import set_multiplex_active, set_secret_scope, reset_secret_scope
from plugins.config_backends.remote import credentials

STAGING = "https://staging.thormarket.site"
OTHER = "https://other.thormarket.site"
LAUNCH_KEY = "sk-thor-launch"
WORK_KEY = "sk-thor-work"


def _profile(home: Path, base_url: str, key: str = LAUNCH_KEY) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text(f"THORHUB_BASE_URL={base_url}\n", encoding="utf-8")
    (home / "auth.json").write_text(json.dumps(
        {"version": 1, "active_provider": "thor", "providers": {"thor": {"api_key": key}}}), encoding="utf-8")
    return home


@pytest.fixture
def launch_home(tmp_path, monkeypatch):
    home = _profile(tmp_path / "thor", STAGING)
    monkeypatch.setenv("THOR_HOME", str(home))
    monkeypatch.setenv("THOR_SHARED_AUTH_DIR", str(tmp_path / "shared"))
    monkeypatch.delenv("THORHUB_BASE_URL", raising=False)
    return home


def _in_fresh_thread(fn):
    """Run ``fn`` on a bare thread, as the poller does: no ContextVar reaches it."""
    out: dict = {}

    def run():
        try:
            out["value"] = fn()
        except BaseException as exc:  # surfaced to the test below
            out["error"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(30)
    assert not t.is_alive(), "token resolution hung"
    if "error" in out:
        raise out["error"]
    return out["value"]


def _no_unscoped_warning(caplog) -> None:
    text = caplog.text
    assert "unreadable" not in text, text
    assert "ignoring invalid portal_base_url" not in text, text


def test_poller_thread_resolves_launch_profiles_own_key(launch_home, caplog):
    set_multiplex_active(True)
    caplog.set_level(logging.WARNING)

    token = _in_fresh_thread(lambda: credentials.plane_token(launch_home))

    assert token == LAUNCH_KEY
    _no_unscoped_warning(caplog)


def test_poller_thread_resolves_secondary_profiles_own_key(launch_home, caplog):
    secondary = _profile(launch_home / "profiles" / "work", OTHER, WORK_KEY)
    set_multiplex_active(True)
    caplog.set_level(logging.WARNING)

    token = _in_fresh_thread(lambda: credentials.plane_token(secondary))

    assert token == WORK_KEY
    _no_unscoped_warning(caplog)


def test_another_profiles_bound_scope_does_not_route_this_profiles_token(launch_home, caplog):
    """A caller bound to the launch profile resolving the secondary's token reads the
    secondary's own key, never the bound one; the caller's scope is back afterwards."""
    from agent.secret_scope import current_secret_scope_home

    secondary = _profile(launch_home / "profiles" / "work", OTHER, WORK_KEY)
    set_multiplex_active(True)
    caplog.set_level(logging.WARNING)

    bound = set_secret_scope({"THORHUB_BASE_URL": STAGING}, profile_home=str(launch_home))
    try:
        assert credentials.plane_token(secondary) == WORK_KEY
        assert current_secret_scope_home() == str(launch_home)
    finally:
        reset_secret_scope(bound)

    _no_unscoped_warning(caplog)


def test_scope_is_reset_when_resolution_fails(launch_home, monkeypatch):
    from agent.secret_scope import current_secret_scope

    set_multiplex_active(True)

    def boom(**_kw):
        assert current_secret_scope() is not None  # bound during the resolution
        raise RuntimeError("network down")

    monkeypatch.setattr("thor_cli.auth_thorhub.resolve_thorhub_access_token", boom)

    def call():
        with pytest.raises(credentials.PlaneCredentialError):
            credentials.plane_token(launch_home)
        return current_secret_scope()

    assert _in_fresh_thread(call) is None


def test_home_and_scope_are_restored_when_the_scope_build_fails(launch_home, monkeypatch):
    from agent.secret_scope import current_secret_scope_home
    from thor_constants import get_thor_home_override, reset_thor_home_override, set_thor_home_override
    from tui_gateway import launch_profile_policy

    secondary = _profile(launch_home / "profiles" / "work", OTHER, WORK_KEY)
    set_multiplex_active(True)

    def boom(_home):
        raise RuntimeError("unreadable managed .env")

    monkeypatch.setattr(launch_profile_policy, "owner_secret_scope", boom)
    home_token = set_thor_home_override(launch_home)
    scope_token = set_secret_scope({"THORHUB_BASE_URL": STAGING}, profile_home=str(launch_home))
    try:
        with pytest.raises(credentials.PlaneCredentialError):
            credentials.plane_token(secondary)
        assert get_thor_home_override() == str(launch_home)
        assert current_secret_scope_home() == str(launch_home)
    finally:
        reset_secret_scope(scope_token)
        reset_thor_home_override(home_token)


def test_launch_profile_keeps_its_env_only_override_frozen_at_activation(tmp_path, monkeypatch):
    """A launch ThorHub override with no .env line (systemd / ``op run``) is the launch profile's
    own: it survives later live-env mutation because the launch scope reads the frozen env."""
    from thor_cli.thorhub_account import thorhub_base_url_env_override

    home = _profile(tmp_path / "thor", STAGING)
    (home / ".env").write_text("", encoding="utf-8")
    monkeypatch.setenv("THOR_HOME", str(home))
    monkeypatch.setenv("THOR_SHARED_AUTH_DIR", str(tmp_path / "shared"))
    monkeypatch.setenv("THORHUB_BASE_URL", STAGING)
    from tui_gateway.launch_profile_policy import activate_multi_profile_hosting, owner_secret_scope
    activate_multi_profile_hosting()  # freezes the launch env
    monkeypatch.setenv("THORHUB_BASE_URL", OTHER)  # poisoned afterwards

    def _read():
        from agent.secret_scope import reset_secret_scope, set_secret_scope
        token = set_secret_scope(owner_secret_scope(home), profile_home=str(home))
        try:
            return thorhub_base_url_env_override()
        finally:
            reset_secret_scope(token)

    assert _in_fresh_thread(_read) == STAGING


def test_secondary_falls_back_to_the_launch_env_not_the_live_env(launch_home, monkeypatch):
    """A secondary with no ThorHub override of its own falls back to the launch profile's
    .env value — never the live process env (ignored under multiplex) — and still reads
    its own key."""
    from thor_cli.thorhub_account import thorhub_base_url_env_override

    secondary = _profile(launch_home / "profiles" / "work", "https://llm.thormarket.site", WORK_KEY)
    (secondary / ".env").write_text("", encoding="utf-8")
    monkeypatch.setenv("THORHUB_BASE_URL", OTHER)  # live env is ignored under multiplex
    set_multiplex_active(True)

    assert _in_fresh_thread(lambda: credentials.plane_token(secondary)) == WORK_KEY

    def _read():
        from agent.secret_scope import reset_secret_scope, set_secret_scope
        from tui_gateway.launch_profile_policy import owner_secret_scope
        token = set_secret_scope(owner_secret_scope(secondary), profile_home=str(secondary))
        try:
            return thorhub_base_url_env_override()
        finally:
            reset_secret_scope(token)

    assert _in_fresh_thread(_read) == STAGING


def test_single_profile_binds_nothing(launch_home, monkeypatch):
    """Not multiplexing: no scope is bound and the process env still routes (unchanged behaviour)."""
    from agent.secret_scope import current_secret_scope
    from thor_cli import auth_thorhub
    from thor_cli.thorhub_account import thorhub_base_url_env_override

    monkeypatch.setenv("THORHUB_BASE_URL", OTHER)
    real = auth_thorhub.resolve_thorhub_access_token
    scopes = []

    def spy(**kw):
        scopes.append(current_secret_scope())
        return real(**kw)

    monkeypatch.setattr(auth_thorhub, "resolve_thorhub_access_token", spy)
    assert credentials.plane_token(launch_home) == LAUNCH_KEY
    assert scopes == [None]
    assert thorhub_base_url_env_override() == OTHER
