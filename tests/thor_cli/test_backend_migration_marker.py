"""The backend-migration marker read by ``thor update`` (Fase 2).

Behaviour contracts only: which manifest states keep the old backend down, and
the fail-closed answer for a manifest that cannot be read.
"""

from __future__ import annotations

import json

from thor_cli.backend_migration_marker import backend_retired_by_migration


def _write(home, text):
    (home / "backend_migration.json").write_text(text, encoding="utf-8")


def test_no_manifest_means_not_retired(tmp_path):
    assert backend_retired_by_migration(tmp_path / "home") is False


def test_done_running_and_failed_states_keep_the_old_backend_down(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    for state in ("done", "running", "failed"):
        _write(home, json.dumps({"state": state}))
        assert backend_retired_by_migration(home) is True, state


def test_restored_and_rolled_back_states_let_the_old_backend_start_again(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    for state in ("restored", "rolled_back"):
        _write(home, json.dumps({"state": state}))
        assert backend_retired_by_migration(home) is False, state


def test_an_unreadable_or_corrupt_manifest_is_fail_closed(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _write(home, "{not json")
    assert backend_retired_by_migration(home) is True
    _write(home, json.dumps(["not", "a", "mapping"]))
    assert backend_retired_by_migration(home) is True
    _write(home, json.dumps({"no_state": True}))
    assert backend_retired_by_migration(home) is True
