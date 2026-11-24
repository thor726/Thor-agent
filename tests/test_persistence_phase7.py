"""Fase 7 persistence support modules: process_identity, session_rescue,
storage_limits, session_keys (+ persistence.core.keys) and the
thor_state_pidns / thor_state delegation shims.
"""

import os
import subprocess
import sys

import pytest

import process_identity
import session_keys
import session_rescue
import storage_limits
import thor_state_pidns
from persistence.core.keys import (
    profile_from_session_key_namespace,
    session_key_profile,
)


def test_pidns_shim_reexports_canonical_names():
    assert thor_state_pidns.holder_pid_checkable is process_identity.holder_pid_checkable
    assert thor_state_pidns.pid_namespace_id is process_identity.pid_namespace_id
    assert thor_state_pidns.holder_namespace_token is process_identity.holder_namespace_token
    assert (
        thor_state_pidns.persistent_record_pidns_checkable
        is process_identity.persistent_record_pidns_checkable
    )
    assert thor_state_pidns.LocalPidNamespace is process_identity.LocalPidNamespace


def test_holder_namespace_token_roundtrip():
    token = process_identity.holder_namespace_token()
    ns = process_identity.pid_namespace_id()
    if ns is None:
        assert token == ""
    else:
        assert token == f":pidns={ns}"
        holder = f"pid={os.getpid()}{token}:turn=abc"
        assert process_identity.holder_pid_checkable(holder) is True


def test_holder_pid_checkable_unstamped_is_strict():
    assert process_identity.holder_pid_checkable("pid=123:turn=abc") is False
    assert process_identity.holder_pid_checkable("") is False
    assert process_identity.holder_pid_checkable("not-a-holder") is False


def test_holder_process_is_dead():
    assert process_identity.holder_process_is_dead("") is False
    assert process_identity.holder_process_is_dead("garbage") is False
    assert process_identity.holder_process_is_dead(f"pid={os.getpid()}") is False
    assert process_identity.holder_process_is_dead("pid=1") is False  # init is alive
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    proc.terminate()
    proc.wait()
    # Unstamped holders defer to TTL by design (STRICT policy), so stamp our
    # own namespace before probing a dead pid.
    holder = f"pid={proc.pid}{process_identity.holder_namespace_token()}:turn=x"
    assert process_identity.holder_process_is_dead(holder) is True
    assert process_identity.holder_process_is_dead(f"pid={proc.pid}:turn=x") is False


def test_thor_state_dead_holder_alias():
    from thor_state import _compression_lock_holder_process_is_dead

    assert _compression_lock_holder_process_is_dead("garbage") is False
    assert _compression_lock_holder_process_is_dead(f"pid={os.getpid()}") is False
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    proc.terminate()
    proc.wait()
    import process_identity as _pi

    holder = f"pid={proc.pid}{_pi.holder_namespace_token()}"
    assert _compression_lock_holder_process_is_dead(holder) is True


def test_session_rescue_writes_jsonl(tmp_path):
    path = session_rescue.divert_session_transcript_jsonl(
        "sess-1",
        [{"role": "user", "content": "hi"}, "plain", None],
        sessions_dir=tmp_path,
    )
    assert path == tmp_path / "sess-1.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"hi"' in lines[0]
    assert '"plain"' in lines[1]


def test_session_rescue_nothing_to_write(tmp_path):
    assert (
        session_rescue.divert_session_transcript_jsonl("", [{"a": 1}], sessions_dir=tmp_path)
        is None
    )
    assert (
        session_rescue.divert_session_transcript_jsonl("s", [], sessions_dir=tmp_path)
        is None
    )
    assert list(tmp_path.glob("*.jsonl")) == []


def test_storage_limits_defaults(monkeypatch):
    import thor_cli.config

    monkeypatch.setattr(
        thor_cli.config, "load_config_readonly", lambda: {"sessions": {}}
    )
    assert storage_limits.resolved_max_resume_messages() == 20_000
    assert storage_limits.resolved_max_export_messages() == 20_000


def test_storage_limits_configured_and_fallback(monkeypatch):
    import thor_cli.config

    monkeypatch.setattr(
        thor_cli.config,
        "load_config_readonly",
        lambda: {"sessions": {"max_resume_messages": 5, "max_export_messages": 0}},
    )
    assert storage_limits.resolved_max_resume_messages() == 5
    assert storage_limits.resolved_max_export_messages() == 0  # 0 disables
    monkeypatch.setattr(
        thor_cli.config,
        "load_config_readonly",
        lambda: {"sessions": {"max_resume_messages": -3}},
    )
    assert storage_limits.resolved_max_resume_messages() == 20_000
    monkeypatch.setattr(
        thor_cli.config, "load_config_readonly", lambda: (_ for _ in ()).throw(RuntimeError("nope"))
    )
    assert storage_limits.resolved_max_resume_messages() == 20_000


def test_session_keys():
    assert session_keys.profile_from_session_key("agent:main:xyz") == "default"
    assert session_keys.profile_from_session_key("agent:main~:xyz") == "main"
    assert session_keys.profile_from_session_key("agent:work:xyz") == "work"
    assert session_keys.profile_from_session_key("") is None
    assert session_keys.profile_from_session_key(None) is None
    assert session_keys.profile_from_session_key("cli:main:xyz") is None
    # Empty namespace slot falls back to "main" upstream, i.e. "default".
    assert session_keys.profile_from_session_key("agent:") == "default"
    assert profile_from_session_key_namespace("main") == "default"
    assert profile_from_session_key_namespace("main~") == "main"
    assert profile_from_session_key_namespace("other") == "other"
    assert session_key_profile("agent:main:abc") == "default"
    assert session_key_profile("agent:work:abc") == "work"
    assert session_key_profile("not-a-key") is None
    assert session_key_profile(None) is None


# --- persistence core contracts (commit 2) -----------------------------------


def test_error_taxonomy():
    from persistence.core.errors import (
        AuthorityRefusal,
        CompressionInProgress,
        DiskFull,
        ExportTooLarge,
        NotFound,
        PersistenceError,
        SessionRowMissing,
        StoreContention,
        StoreQuarantined,
        StoreReplaced,
        TransientStoreError,
    )

    assert issubclass(AuthorityRefusal, PersistenceError)
    assert issubclass(AuthorityRefusal, ValueError)
    assert issubclass(SessionRowMissing, NotFound)
    assert issubclass(StoreContention, TransientStoreError)
    assert issubclass(DiskFull, TransientStoreError)
    assert issubclass(StoreQuarantined, PersistenceError)
    assert issubclass(CompressionInProgress, PersistenceError)
    assert issubclass(ExportTooLarge, ValueError)
    err = StoreReplaced("db was replaced")
    assert isinstance(err, PersistenceError) and isinstance(err, RuntimeError)
    assert err.cause == "replaced"


def test_identity_paging():
    from persistence.core.identity import Page, PageRequest

    with pytest.raises(ValueError):
        PageRequest(limit=0)
    req = PageRequest(limit=10)
    assert req.limit == 10 and req.cursor is None
    page = Page(items=(1, 2), continuation=None)
    assert page.items == (1, 2)


def test_stored_instant():
    from datetime import datetime, timezone

    from persistence.core.conventions import (
        RowVisibility,
        UNTRUSTED_INSTANT,
        ensure_utc,
        stored_instant,
    )

    assert stored_instant(None) is None
    assert stored_instant("") is None
    instant = stored_instant(1_700_000_000)
    assert instant is not None and instant.tzinfo is timezone.utc
    assert abs(instant.timestamp() - 1_700_000_000) < 1e-6
    assert stored_instant("not-a-number") is None
    assert stored_instant(float("inf")) is None
    assert stored_instant(-5) is None  # outside the trust window
    assert stored_instant(5_000_000_000) is None  # outside the trust window
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert stored_instant(aware) == aware
    with pytest.raises(ValueError):
        ensure_utc(datetime(2026, 1, 1))  # naive rejected
    assert UNTRUSTED_INSTANT.timestamp() == 0.0
    assert {v.value for v in RowVisibility} == {
        "active",
        "rewound",
        "compaction_archived",
    }


def test_authority_vocabulary():
    from persistence.authority.vocabulary import (
        ADMISSION_QUEUE_MAX,
        LEGACY_CREATION_SOURCES,
        LEGACY_LOCAL_SOURCES,
        NOT_CLIENT_LABELS,
        OwnerRule,
        admission_fingerprint,
    )

    assert ADMISSION_QUEUE_MAX == 32
    assert "cli" in LEGACY_LOCAL_SOURCES and "telegram" not in LEGACY_LOCAL_SOURCES
    assert LEGACY_CREATION_SOURCES == {"desktop": "gui"}
    assert "cron" in NOT_CLIENT_LABELS
    rule = OwnerRule(
        host_subject="uid:1000",
        login_providers=frozenset({"thor"}),
        messaging_labels=frozenset({"telegram"}),
    )
    assert rule.host_subject == "uid:1000"
    fp1 = admission_fingerprint(canonical_target="sess", payload={"a": 1})
    fp2 = admission_fingerprint(canonical_target="sess", payload={"a": 1})
    assert fp1 == fp2 and isinstance(fp1, str) and fp1
    assert admission_fingerprint(
        canonical_target="other", payload={"a": 1}
    ) != fp1
