"""Regression tests for the Thor Portal env-override bypassing the host
allowlist, mirroring the existing THOR_PORTAL_INFERENCE_BASE_URL /
_ALLOWED_THOR_PORTAL_INFERENCE_HOSTS treatment.

Real incident (2026-07): a hosted agent provisioned by thor-account-service
on the `staging` Vercel environment is stamped with
``THOR_PORTAL_BASE_URL=https://portal.staging-thor-agent.local`` in its
container env (the documented dev/staging override), while its bootstrap
``auth.json`` ALSO persists ``portal_base_url`` to the same staging host.

Before this fix, ``resolve_thor_access_token`` / ``resolve_thor_runtime_
credentials`` read ``state.get("portal_base_url")`` FIRST via a plain ``or``
chain, so whenever the stored state had ANY value the env vars were never
even consulted — and whichever value won (state or env) was then run through
``_THOR_PORTAL_ALLOWED_HOSTS``, which only recognised the production host.
The staging host was silently rewritten back to prod on every refresh, so a
staging-issued refresh token got replayed against the PROD token endpoint.
Prod correctly rejected that with ``invalid_grant``, which triggered
``_quarantine_thor_oauth_state`` and wiped the entire credential pool.

The correct fix (mirroring ``_thor_inference_env_override()``): the env
override is a TRUSTED value the operator/deployment set themselves — it must
win outright (even over a stored value) and bypass the allowlist entirely.
The allowlist exists only to reject an untrusted NETWORK-provided value
(a poisoned portal_base_url written to auth.json by a compromised Portal
response), never a value the operator explicitly configured.
"""

from __future__ import annotations

import json
import logging

from thor_cli.auth import (
    DEFAULT_THOR_PORTAL_URL,
)


class TestResolveAccessTokenEnvOverrideWins:
    """End-to-end: resolve_thor_access_token must use the env override for
    the refresh call, bypassing the allowlist, even when state also has a
    portal_base_url set (the exact incident shape)."""

    def _write_auth_file(self, tmp_path, *, stored_portal_url):
        auth_file = tmp_path / "auth.json"
        auth_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "active_provider": "thor",
                    "providers": {
                        "thor": {
                            "portal_base_url": stored_portal_url,
                            "access_token": "expired-access",
                            "refresh_token": "staging-refresh",
                            "client_id": "thor-cli-vps",
                            "expires_at": "2000-01-01T00:00:00+00:00",
                        }
                    },
                }
            )
        )
        return auth_file

    def _run_and_capture(self, monkeypatch, auth):
        from thor_cli import auth_thor
        seen_portal_urls = []

        # The resolve memo is module-level state; clear it so each test's
        # resolution actually exercises the refresh path instead of serving
        # a token cached by a previous test.
        monkeypatch.setattr(auth, "_RESOLVE_TOKEN_CACHE", {})

        def _fake_refresh(*, client, portal_base_url, client_id, refresh_token):
            seen_portal_urls.append(portal_base_url)
            return {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            }

        monkeypatch.setattr(auth, "_refresh_access_token", _fake_refresh)
        monkeypatch.setattr(auth_thor, "_refresh_access_token", _fake_refresh)

        caplog_records = []
        logger = logging.getLogger("thor_cli.auth")
        handler = logging.Handler()
        handler.emit = lambda record: caplog_records.append(record.getMessage())
        logger.addHandler(handler)
        try:
            auth.resolve_thor_access_token()
        finally:
            logger.removeHandler(handler)
        return seen_portal_urls, caplog_records

    def test_env_override_wins_even_with_staging_state_stored(
        self, monkeypatch, tmp_path
    ):
        """The real incident: state ALSO has the staging host stored (from
        a prior THOR_AUTH_JSON_BOOTSTRAP seed), and the env var is set to
        the same staging host. Both must resolve to staging, and the
        allowlist-rejection warning must never fire."""
        from thor_cli import auth

        staging_portal = "https://portal.staging-thor-agent.local"
        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        monkeypatch.setenv("THOR_PORTAL_BASE_URL", staging_portal)
        self._write_auth_file(tmp_path, stored_portal_url=staging_portal)

        seen_portal_urls, records = self._run_and_capture(monkeypatch, auth)

        assert seen_portal_urls == [staging_portal]
        assert not any(
            "ignoring invalid portal_base_url" in msg for msg in records
        ), "env override must bypass the allowlist gate entirely"



    def test_no_env_no_staging_state_prod_url_used_unmodified(
        self, monkeypatch, tmp_path
    ):
        """Baseline: no override, no staging state — prod is used and the
        allowlist never even logs a warning (nothing was rejected)."""
        from thor_cli import auth

        monkeypatch.setenv("THOR_HOME", str(tmp_path))
        monkeypatch.delenv("THOR_PORTAL_BASE_URL", raising=False)
        monkeypatch.delenv("THOR_PORTAL_BASE_URL", raising=False)
        self._write_auth_file(tmp_path, stored_portal_url=DEFAULT_THOR_PORTAL_URL)

        seen_portal_urls, records = self._run_and_capture(monkeypatch, auth)

        assert seen_portal_urls == [DEFAULT_THOR_PORTAL_URL]
        assert not any("ignoring invalid portal_base_url" in msg for msg in records)
