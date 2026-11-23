"""The one-time free-tier notice flag — retired with the guest free tier.

There is no free tier anymore, so no notice is ever pending and marking it shown is a
no-op: ``guest_notice_pending()`` is always False and ``mark_guest_notice_shown()`` always
False, whatever identity (or legacy guest state) the store holds. Nothing is written.
"""

from __future__ import annotations

import pytest

from thor_cli import anon_auth
from thor_cli.auth import _auth_store_lock, _load_auth_store, _save_auth_store


def _write_state(state: dict) -> None:
    with _auth_store_lock():
        store = _load_auth_store()
        store.setdefault("providers", {}).update(state)
        _save_auth_store(store)


@pytest.mark.parametrize("state", [
    {},
    {"nous": {"auth_method": "anonymous", "access_token": "legacy-guest-jwt",
              "account_tier": "anonymous"}},
    {"thor": {"api_key": "sk-thor-test"}},
])
def test_no_notice_is_ever_pending(tmp_path, monkeypatch, state):
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    _write_state(state)
    assert anon_auth.guest_notice_pending() is False
    assert anon_auth.mark_guest_notice_shown() is False
    assert anon_auth.GUEST_NOTICE_FLAG not in _load_auth_store().get("providers", {}).get("nous", {})
