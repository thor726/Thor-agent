"""Minimal ``profiles_run_elsewhere`` reader: the preflight check for
``thor gateway migrate --backends`` (see ``thor_cli/profiles_run_elsewhere.py``).

Behaviour contracts only: a marker file marks its profile (an unreadable one still
marks it), a missing folder marks nothing, and a folder that cannot be read for any
other reason marks every profile (fail-closed, as the desktop reader does).
"""

from __future__ import annotations

import json

from thor_cli import profiles_run_elsewhere as pre


def _write_marker(root, profile, payload):
    folder = root / pre.RUN_ELSEWHERE_DIRNAME
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{profile}.json").write_text(json.dumps(payload), encoding="utf-8")
    return folder


def test_marker_marks_profile_names_plugin_and_unreadable_marker_still_marks(tmp_path):
    root = tmp_path / "root"
    _write_marker(root, "default", {"plugin": "sandbox-plugin", "since": "2026-11-27T00:00:00Z"})

    entry = pre.run_elsewhere_for_home(root)
    assert entry is not None and entry.plugin == "sandbox-plugin"
    assert "sandbox-plugin" in entry.backend_note() and "does not move" in entry.backend_note()
    refusal = pre.run_elsewhere_refusal(root)
    assert refusal is not None and "sandbox-plugin" in refusal and "default" in refusal

    # A marker for another profile does not mark this home.
    assert pre.run_elsewhere_for_home(root / "profiles" / "ops") is None
    _write_marker(root, "ops", {"plugin": "sandbox-plugin"})
    assert pre.run_elsewhere_for_home(root / "profiles" / "ops") is not None

    # A marker that cannot be read still marks the profile; only its owner is unknown.
    (root / pre.RUN_ELSEWHERE_DIRNAME / "default.json").write_text("not json {", encoding="utf-8")
    entry = pre.run_elsewhere_for_home(root)
    assert entry is not None and entry.plugin is None
    assert "does not move" in entry.backend_note()  # still marked; only its owner is unknown
    assert "could not be read" in entry.message()
    assert pre.run_elsewhere_refusal(root) is not None


def test_missing_folder_marks_nothing_but_unreadable_folder_marks_every_profile(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    assert pre.run_elsewhere_for_home(root) is None
    assert pre.run_elsewhere_refusal(root) is None
    assert pre.run_elsewhere_for_home(root / "profiles" / "ops") is None

    # A file where the marker folder belongs: the folder cannot be listed for a reason
    # other than missing or permission denied, so every profile is marked (fail-closed).
    (root / pre.RUN_ELSEWHERE_DIRNAME).write_text("not a folder", encoding="utf-8")
    for home in (root, root / "profiles" / "ops"):
        entry = pre.run_elsewhere_for_home(home)
        assert entry is not None and entry.folder_error is not None
        assert "cannot read" in entry.backend_note()
    assert pre.run_elsewhere_refusal(root) is not None
