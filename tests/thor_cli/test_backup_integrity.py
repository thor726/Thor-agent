"""Behaviour contracts for ``thor_cli.backup_integrity`` (port of upstream
``hermes_cli.backup_integrity``): SQLite verification lives in its own module
and ``thor_cli.backup`` re-exports it, and store files (``state.db``,
``shared-state.db``) are verified by their store admin instead of the raw
SQLite path.
"""

import sqlite3

import pytest

from thor_cli import backup, backup_integrity


@pytest.fixture()
def valid_db(tmp_path):
    path = tmp_path / "other.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO sessions (name) VALUES (?)", [(f"s{i}",) for i in range(10)])
    conn.commit()
    conn.close()
    return path


def test_verify_sqlite_integrity_via_new_module(valid_db, tmp_path):
    """The verifier lives in ``thor_cli.backup_integrity`` and ``thor_cli.backup``
    re-exports the same function, so the restore/update flows that import it
    from ``backup`` keep working."""
    assert backup.verify_sqlite_integrity is backup_integrity.verify_sqlite_integrity
    assert backup_integrity.verify_sqlite_integrity(valid_db)["valid"] is True
    zeroed = tmp_path / "zeroed.db"
    zeroed.write_bytes(b"\x00" * valid_db.stat().st_size)
    assert backup_integrity.verify_sqlite_integrity(zeroed)["valid"] is False


def test_store_file_delegates_to_store_admin(tmp_path, monkeypatch):
    """A store file (``state.db``) is verified by its store admin, not by the
    raw SQLite path; a non-store file never reaches the admin."""
    calls = []

    class FakeAdmin:
        def verify_file(self, path, max_bytes=None):
            calls.append(path)
            return {"valid": True, "message": "admin ok", "size": 123}

    monkeypatch.setattr(backup_integrity, "open_store_admin", lambda path: FakeAdmin())
    monkeypatch.setattr(backup_integrity, "AdminUnsupported", type("NoAdmin", (), {}))

    store_db = tmp_path / "state.db"
    assert backup_integrity.verify_sqlite_integrity(store_db) == {
        "valid": True, "message": "admin ok", "size": 123}
    assert calls == [store_db]

    other = tmp_path / "other.db"
    conn = sqlite3.connect(other)
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.commit()
    conn.close()
    assert backup_integrity.verify_sqlite_integrity(other)["valid"] is True
    assert calls == [store_db]  # the non-store file never reached the admin


def test_store_file_unsupported_admin_is_invalid(tmp_path, monkeypatch):
    """When the backend reports the admin capability unsupported, verification
    fails with the capability named instead of silently falling back."""

    class FakeUnsupported:
        capability = "physical admin"
        backend_kind = "sqlite"

    monkeypatch.setattr(backup_integrity, "open_store_admin", lambda path: FakeUnsupported())
    monkeypatch.setattr(backup_integrity, "AdminUnsupported", FakeUnsupported)

    res = backup_integrity.verify_sqlite_integrity(tmp_path / "shared-state.db")
    assert res["valid"] is False
    assert "physical admin" in res["message"]
    assert "sqlite" in res["message"]
