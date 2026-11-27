"""Profiles a plugin runs elsewhere: the minimal preflight reader for
``thor gateway migrate --backends``.

This is NOT the full ``profiles_run_elsewhere`` feature (gap #7): it contains only
:func:`run_elsewhere_for_home` and :func:`run_elsewhere_refusal`, the two answers the
migration preflight needs. A host-side plugin that runs a profile's whole backend
elsewhere (for example inside a sandbox) marks the profile for as long as it does, with
one file per profile: ``<thor root>/profiles_run_elsewhere/<profile>.json``. The file's
presence is the marker; its contents (``{"plugin": ..., "since": ...}``) only name the
owner in messages, so a marker that cannot be read still marks the profile.

Fail-closed, the way the desktop reader does
(``apps/desktop/electron/profile-runs-elsewhere.ts``): a marker folder that cannot be
listed for any reason other than missing or permission denied marks every profile, and
a process denied the folder (permission error) is the backend a plugin runs elsewhere,
so it refuses nothing.

Limitations of this minimal reader (all gap #7 territory, not this module):

- Only the migration preflight asks it. Other hosts (``thor gateway ensure``,
  ``thor serve`` / ``dashboard``, cron, the gateway) still do NOT refuse a marked
  profile — a migrated-to gateway would refuse it, but a host process may still
  start it.
- A marker is followed only under the names the home's own path carries (as written
  and resolved). It is not followed under another name whose home is the same
  directory (a profile that is a link to a marked profile's home).
- There is no caching, no mark/clear writer, and no per-value ``home_runs_elsewhere``
  check: this module only answers one home at a time, on demand.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from thor_constants import PROFILE_ID_RE

logger = logging.getLogger(__name__)

RUN_ELSEWHERE_DIRNAME = "profiles_run_elsewhere"
_SUFFIX = ".json"
_logged: set[str] = set()


@dataclass(frozen=True)
class RunElsewhere:
    """Why this host does not run ``profile``.

    ``plugin`` is None when the marker could not be read. ``folder_error`` is set when the marker
    folder itself could not be read, which refuses every profile.
    """

    profile: str
    path: Path
    plugin: str | None = None
    since: str | None = None
    folder_error: str | None = None

    def message(self) -> str:
        if self.folder_error is not None:
            return (f"Thor cannot read {self.path.parent} ({self.folder_error}), so it cannot tell "
                    f"whether a plugin runs profile '{self.profile}' elsewhere. It does not run the "
                    "profile on this host until it can read that folder.")
        if self.plugin is None:
            return (f"Profile '{self.profile}' runs elsewhere: a plugin runs its backend (its marker "
                    f"{self.path} could not be read), so Thor does not run it on this host. Use the "
                    "profile from the Thor desktop app, or turn this off in the plugin (or delete the "
                    "marker) to run it here.")
        return (f"Profile '{self.profile}' runs elsewhere: the '{self.plugin}' plugin runs its backend, "
                "so Thor does not run it on this host. Use the profile from the Thor desktop app, "
                f"or turn this off in the '{self.plugin}' plugin to run it here. If that plugin is no "
                "longer installed or no longer loads, deleting {self.path} lets Thor run the profile "
                "on this host again; do not delete it while the plugin still runs the profile.")

    def backend_note(self) -> str:
        """One line for the lists of ``thor serve`` / ``thor dashboard`` backends (the backend
        migration's report): a backend of this home is not one to move."""
        if self.folder_error is not None:
            return (f"Thor cannot read {self.path.parent}, so it cannot tell whether a plugin runs "
                    f"profile '{self.profile}' elsewhere: it does not move this backend to the gateway "
                    "on this host.")
        owner = f"the '{self.plugin}' plugin runs" if self.plugin is not None else "a plugin runs"
        return (f"Profile '{self.profile}' runs elsewhere ({owner} its backend): Thor does not move "
                "this backend to the gateway on this host.")


def run_elsewhere_dir(root: str | Path | None = None) -> Path:
    """The marker folder under *root* (default: this process's Thor root)."""
    if root is None:
        from thor_constants import get_default_thor_root
        root = get_default_thor_root()
    return Path(root) / RUN_ELSEWHERE_DIRNAME


def _is_profile_id(name: str) -> bool:
    return name == "default" or bool(PROFILE_ID_RE.match(name))


def _log_once(level: int, message: str, *args) -> None:
    key = message % args
    if key not in _logged:
        _logged.add(key)
        logger.log(level, message, *args)


@dataclass(frozen=True)
class _MarkerFolder:
    """One listing of the marker folder: the profile ids it marks, and ``error`` when the folder
    could not be read (no profile may run here then)."""

    names: frozenset[str] = frozenset()
    error: OSError | None = None


def _read_folder(folder: Path) -> _MarkerFolder:
    try:
        names = os.listdir(folder)
    except FileNotFoundError:
        return _MarkerFolder()
    except PermissionError:
        _log_once(logging.INFO, "Cannot list %s (permission denied): this process is a backend a "
                  "plugin runs elsewhere, so it refuses no profile", folder)
        return _MarkerFolder()
    except OSError as exc:  # a file where the folder belongs, an I/O error, ...
        _log_once(logging.ERROR, "Cannot read %s (%s); running no profile until it can be read",
                  folder, exc)
        return _MarkerFolder(error=exc)
    # Writers stage a marker under a dot-prefixed name; any name but <profile>.json is not a marker.
    return _MarkerFolder(frozenset(name[:-len(_SUFFIX)] for name in names
                                   if name.endswith(_SUFFIX) and _is_profile_id(name[:-len(_SUFFIX)])))


def _read_entry(folder: Path, profile: str) -> RunElsewhere:
    path = folder / f"{profile}{_SUFFIX}"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return RunElsewhere(profile, path)
    if not isinstance(data, dict):
        return RunElsewhere(profile, path)
    plugin, since = data.get("plugin"), data.get("since")
    return RunElsewhere(profile, path, plugin if isinstance(plugin, str) and plugin.strip() else None,
                        since if isinstance(since, str) else None)


def _entry_in(listing: _MarkerFolder, folder: Path, profile: str) -> RunElsewhere | None:
    """What one listing of *folder* says about *profile*: the folder's error, its marker, or None."""
    if listing.error is not None:
        return RunElsewhere(profile, folder / f"{profile}{_SUFFIX}", folder_error=str(listing.error))
    return _read_entry(folder, profile) if profile in listing.names else None


def _home_readings(home: Path) -> list[tuple[str, Path]]:
    """``(profile, root)`` for *home* as written and as resolved, without repeats:
    ``<root>/profiles/<id>`` is that named profile of ``<root>``; any other home is the default
    profile of the root it is."""
    spellings = [home]
    try:
        spellings.append(home.resolve(strict=False))
    except (OSError, RuntimeError):  # a link loop: only the written path is left to read
        pass
    readings: list[tuple[str, Path]] = []
    for path in spellings:
        name = path.name.lower()  # ids are stored lowercase; a case-insensitive volume opens any case
        named = path.parent.name == "profiles" and name != "default" and _is_profile_id(name)
        reading = (name, path.parent.parent) if named else ("default", path)
        if reading not in readings:
            readings.append(reading)
    return readings


def run_elsewhere_for_home(home: str | Path) -> RunElsewhere | None:
    """:func:`run_elsewhere` for the profile whose home is *home*.

    *home* is read both as written and resolved, so another path to a profile home (a symlink or
    junction, a relative or ``..`` path, another letter case) reaches that profile's marker. A
    marker under either reading refuses, so neither reading can hide the other's.
    """
    # os.path.expanduser leaves a "~name" that is no user's as written, as the read of a file under
    # it does; Path.expanduser raises for it.
    home = Path(os.path.expanduser(home))
    for profile, root in _home_readings(home):
        folder = run_elsewhere_dir(root)
        if (entry := _entry_in(_read_folder(folder), folder, profile)) is not None:
            return entry
    return None


def run_elsewhere_refusal(home: str | Path | None = None) -> str | None:
    """Why this host must not run the profile at *home* (default: this process's Thor home),
    as a message, or None when the profile at *home* runs here."""
    if home is None:
        from thor_constants import get_thor_home
        home = get_thor_home()
    entry = run_elsewhere_for_home(home)
    return None if entry is None else entry.message()
