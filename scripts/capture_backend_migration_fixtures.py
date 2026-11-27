#!/usr/bin/env -S bash -c 'exec "$BASH" "$(dirname "$0")/run-in-thor-env" python3 "$0" "$@"'
"""Re-capture the dashboard's backend-migration fixtures from Thor's own engine.

The dashboard card (``web/src/components/BackendMigrationCard.tsx``) renders
engine outputs it cannot invent: plan payloads, ``--status`` payloads, refusal
blockers and every step string the engine prints for each supervisor kind.
Those payloads live in ``BackendMigrationCard.plans.fixture.ts`` and
``BackendMigrationCard.engine.fixture.ts``; this script regenerates them by
driving the real engine (``build_plan`` / ``apply`` / ``restore`` /
``recover_interrupted`` / ``rollback``) plus the real dashboard routes via
``TestClient`` (``/api/gateway/migrate/backends/plan`` and ``.../status``),
against temporary homes under one capture root. Nothing here is a test and
nothing under ``tests/`` imports it: run it by hand when the engine changes
and the card's fixtures need to follow.

Usage (from the repo root)::

    ./scripts/capture_backend_migration_fixtures.py            # --check (default)
    ./scripts/capture_backend_migration_fixtures.py --write DIR
    ./scripts/capture_backend_migration_fixtures.py --root DIR --keep-root

``--check`` captures and compares against the committed fixtures, normalized:
the capture root, the checkout path and the run's timestamps are placeholders
on both sides (a fresh capture never reproduces the recorded tmp paths or
clock byte for byte), and a divergence is reported per export instead of
overwriting anything. ``--write DIR`` writes fresh fixture files to ``DIR``
(never into the repo) so they can be diffed by hand; it refuses when the
capture diverges from the committed fixtures unless ``--force`` is given.

What is hand-made, and why (the engine cannot produce these on its own):

- ``killedWhileWritingStatus`` / ``exit5BundleStatus``: a manifest is built
  with the real ``new_manifest`` and then edited by hand into the interrupted
  shape (a run killed mid-write leaves ``files_after_apply`` at ``"writing"``
  for the file it was writing, which must DIFFER from its backup; an exit-5
  journal lists ``stop_old_backend`` as entered but not ``write_config``),
  and ``rollback`` is called on it directly with the failure's own words.
- ``planWhileRunning``: a ``running`` manifest whose pid is this process
  (alive), so the plan route reports the run as live.
- ``relativeLauncherStatus`` / ``restoreRefusedStatus``: a refusal the
  detached run records (``record_refusal``), read back through the real
  ``--status`` route.
- ``engineStepStrings``: the sorted union of every step string the probes
  produce — plan ``unsupported`` steps (as the route qualifies them and raw),
  status ``manual_steps`` (qualified and raw), and the rollback/restore
  manual steps for each backup state (restored, edited-since, backup gone,
  stopped-while-writing). The probe homes are the shapes the steps depend
  on: a plain POSIX home, one with a space, a Windows home (``C:/Users/u/.thor``
  and one with a space), and the short ``/h``.

Runtime note: the two exit-5 captures each wait out the engine's 60 s
rollback-verify window (``ROLLBACK_VERIFY_SECONDS``) because the old backend
is deliberately left unverifiable; the script takes ~2 minutes total.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

# The repo root is the parent of this script's directory, whatever the cwd is.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from thor_cli import gateway_migrate_backends_apply as apply_mod
from thor_cli import gateway_migrate_backends_plan as plan_mod
from thor_cli.gateway_migrate_backends import BackendItem
from thor_cli.gateway_migrate_backends_host import FileChangedSinceBackup, SystemHost

FIXTURE_DIR = ROOT_DIR / "web" / "src" / "components"
ENGINE_FIXTURE = FIXTURE_DIR / "BackendMigrationCard.engine.fixture.ts"
PLANS_FIXTURE = FIXTURE_DIR / "BackendMigrationCard.plans.fixture.ts"

# The tmp root and checkout path the committed fixtures were captured under.
FIXTURE_ROOT = "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0"
FIXTURE_CWD = "/home/hatch/workspace/thor-port-migrate"

_CONFIG_BEFORE = "model:\n  default: gemini-3.5-flash\n"
_ENV_BEFORE = "THOR_DASHBOARD_BASIC_AUTH_USERNAME=spike\n"
_PID = 4242
_START = 5242
_PORT = 9119
_PASSWORD = "capture-password-value"
_AUTH_ENV = {"THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike",
             "THOR_DASHBOARD_BASIC_AUTH_PASSWORD": _PASSWORD,
             "THOR_DASHBOARD_BASIC_AUTH_SECRET": "capture-secret-value"}


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Rendering and normalized comparison
# ---------------------------------------------------------------------------

ENGINE_HEADER = """// Engine outputs, captured from Thor's own engine (Fase 5, adaptasi A13).
// Do not hand-edit the payloads: re-run the capture script instead:
//   scripts/capture_backend_migration_fixtures.py [--check | --write DIR]
"""

PLANS_HEADER = """// Backend-migration plan payloads, captured from Thor's own engine (Fase 5, adaptasi A13).
// Do not hand-edit the payloads: re-run the capture script instead:
//   scripts/capture_backend_migration_fixtures.py [--check | --write DIR]
"""

_TIME_KEYS = ("started_at", "finished_at", "now")


def render_fixture(header: str, exports: dict[str, object]) -> str:
    """The fixture file text for *exports*, in the committed shape."""
    parts = [header.rstrip("\n")]
    for name, value in exports.items():
        parts.append(f"export const {name} = {json.dumps(value, indent=2, ensure_ascii=False)};")
    return "\n\n".join(parts) + "\n"


def _normalize_text(text: str, root: str) -> str:
    """One side of the comparison with its run-specific values blanked."""
    for old, new in ((root, "<ROOT>"), (root.replace("/", "\\"), "<ROOT>"),
                     (FIXTURE_ROOT, "<ROOT>"), (FIXTURE_ROOT.replace("/", "\\"), "<ROOT>"),
                     (str(ROOT_DIR), "<CWD>"), (str(ROOT_DIR).replace("/", "\\"), "<CWD>"),
                     (FIXTURE_CWD, "<CWD>"), (FIXTURE_CWD.replace("/", "\\"), "<CWD>")):
        text = text.replace(old, new)
    return text


def _normalize_value(value, root: str):
    """The parsed side: timestamps and the plan token are per-run values."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in _TIME_KEYS and isinstance(item, float) and item != 0.0:
                out[key] = "<TIME>"
            elif key == "expect_token" and item:
                out[key] = "<TOKEN>"
            else:
                out[key] = _normalize_value(item, root)
        return out
    if isinstance(value, list):
        return [_normalize_value(item, root) for item in value]
    if isinstance(value, str):
        return _normalize_text(value, root)
    return value


def _split_exports(text: str) -> dict[str, str]:
    """Each ``export const NAME = ...;`` block of a fixture file, by name."""
    parts = re.split(r"(?m)^export const (\w+) = ", text)
    exports: dict[str, str] = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        exports[name] = body.rstrip("\n").removesuffix(";")
    return exports


def compare_fixtures(rendered: str, committed_path: Path, root: str,
                     only: set[str] | None = None) -> list[str]:
    """Normalized per-export diffs between *rendered* and the committed file."""
    committed = committed_path.read_text(encoding="utf-8-sig")
    problems: list[str] = []
    new = _split_exports(rendered)
    old = _split_exports(committed)
    for name in sorted(set(new) | set(old)):
        if only is not None and name not in only:
            continue
        if name not in new:
            problems.append(f"{committed_path.name}: {name} missing from the capture")
            continue
        if name not in old:
            problems.append(f"{committed_path.name}: {name} is new in the capture")
            continue
        try:
            new_value = _normalize_value(json.loads(new[name]), root)
        except ValueError as exc:
            problems.append(f"{committed_path.name}: {name} is not valid JSON in the capture ({exc})")
            continue
        try:
            old_value = _normalize_value(json.loads(old[name]), FIXTURE_ROOT)
        except ValueError as exc:
            problems.append(f"{committed_path.name}: {name} is not valid JSON in the fixture ({exc})")
            continue
        if new_value == old_value:
            continue
        new_text = json.dumps(new_value, indent=2, ensure_ascii=False).splitlines()
        old_text = json.dumps(old_value, indent=2, ensure_ascii=False).splitlines()
        diff = "\n".join(difflib.unified_diff(old_text, new_text, "committed", "captured",
                                              lineterm="", n=2))
        problems.append(f"{committed_path.name}: {name} diverges:\n{diff}")
    return problems


# ---------------------------------------------------------------------------
# Homes and hosts
# ---------------------------------------------------------------------------

class Capture:
    """One capture run: a fresh root, scenario homes under it, one TestClient."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._old_environ: dict[str, str | None] = {}

    def home(self, name: str) -> Path:
        """A scenario home (created with a config.yaml and .env)."""
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "config.yaml").write_text(_CONFIG_BEFORE, encoding="utf-8")
        (path / ".env").write_text(_ENV_BEFORE, encoding="utf-8")
        os.chmod(path / ".env", 0o660)
        return path

    def setenv(self, key: str, value: str | None) -> None:
        """A process-env override, restored by :meth:`restore_env`."""
        if key not in self._old_environ:
            self._old_environ[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def restore_env(self) -> None:
        for key, value in self._old_environ.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._old_environ.clear()

    def client(self, host_factory):
        """A TestClient over the real dashboard app, answering from *host_factory*."""
        from fastapi.testclient import TestClient

        from thor_cli import web_server
        from thor_cli.web_routers import backend_migration as routes

        routes._host = host_factory
        client = TestClient(web_server.app)
        client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
        return client


def _item(home: Path, *, supervisor: str, scope: str = "user", pid: int = _PID,
          running: bool = True, state: str = "enabled",
          argv: list[str] | None = None, unit: str = "thor-dashboard.service",
          unit_path: str | None = None) -> BackendItem:
    return BackendItem(supervisor=supervisor, running=running, pid=pid,
                       argv=argv if argv is not None else ["/usr/bin/thor", "dashboard", "--no-open",
                                                          "--host", "0.0.0.0", "--port", str(_PORT)],
                       unit=unit, scope=scope,
                       unit_path=unit_path or f"/home/u/.config/systemd/user/{unit}",
                       state=state, thor_home=str(home), this_home=True)


class PlanHost(SystemHost):
    """A host for ``build_plan``: real temp-home files, stubbed services.

    Every probe the planner makes is answered here, so no system service, no
    process table and no network is ever touched. ``turns`` is the old
    backend's running-turn count (``None``: its activity cannot be read);
    ``unknown_turn_files`` names the marker files at fault in that case.
    """

    def __init__(self, home, *, items=None, config=None, env=None, turns=0,
                 unknown_turn_files=None, http=None, health=None, bundle=None,
                 gateway=None, linger=None, family="linux", unit_props=None,
                 process_env=None, process_cwd=None, dropin=None,
                 migrated_webapp=None, config_problem=None, gateway_preflight=None,
                 foreign_gateway_home=None, legacy_gateway_units=None,
                 gateway_owner=("own", None), own_unit=None, same_process_value=None,
                 same_ns=True, unit_launcher_env=None, dotenv=None):
        super().__init__(home)
        self._items = items if items is not None else []
        self._config = config if config is not None else {}
        self._env = env if env is not None else {}
        self._turns = turns
        self._unknown_turn_files = unknown_turn_files or []
        self._http = http if http is not None else {"health": "ok", "auth_required": False,
                                                    "auth_providers": []}
        self._health = health if health is not None else self._http
        self._bundle = bundle
        self._gateway = gateway if gateway is not None else {"kind": "systemd", "unit": "thor-gateway",
                                                            "installed": True, "enabled": True,
                                                            "active": False, "running_pid": None}
        self._linger = linger
        self._family = family
        self._unit_props = unit_props or {}
        self._process_env = process_env or {}
        self._process_cwd = process_cwd
        self._dropin = dropin
        self._migrated_webapp = migrated_webapp
        self._config_problem = config_problem
        self._gateway_preflight = gateway_preflight
        self._foreign_gateway_home = foreign_gateway_home
        self._legacy_gateway_units = legacy_gateway_units
        self._gateway_owner = gateway_owner
        self._own_unit = own_unit
        self._same_process_value = same_process_value
        self._same_ns = same_ns
        self._unit_launcher_env = unit_launcher_env or {}
        self._dotenv = dotenv if dotenv is not None else {}

    def backends(self):
        return list(self._items)

    def is_root(self):
        return False

    def os_family(self):
        return self._family

    def unit_props(self, unit, scope):
        return dict(self._unit_props.get((unit, scope), {"UnitFileState": "enabled",
                                                         "ActiveState": "active",
                                                         "ControlGroup": f"/fake/{unit}"}))

    def process_env(self, pid):
        return dict(self._process_env)

    def process_cwd(self, pid):
        return self._process_cwd

    def start_time(self, pid):
        return 1000 + pid if pid else None

    def same_process(self, pid, start_time):
        if self._same_process_value is not None:
            return self._same_process_value
        return super().same_process(pid, start_time)

    def own_unit(self):
        return self._own_unit

    def running_turns(self, pid, start_time):
        return self._turns

    def unknown_turn_files(self, pid, start_time):
        return list(self._unknown_turn_files)

    def bundle_missing(self):
        return self._bundle

    def gateway_kind(self):
        return (self._gateway or {}).get("kind")

    def gateway_state(self):
        return dict(self._gateway)

    def gateway_preflight(self):
        return self._gateway_preflight

    def legacy_unit_records(self):
        return []

    def linger(self):
        return self._linger

    def gateway_owner(self):
        return self._gateway_owner

    def http_status(self, host, port):
        return dict(self._http) if self._http is not None else None

    def health_status(self, host, port):
        return dict(self._health) if self._health is not None else None

    def same_network_namespace(self, pid, *, container):
        return self._same_ns

    def unit_launcher_env(self, unit, scope):
        return dict(self._unit_launcher_env)

    def dotenv(self):
        return dict(self._dotenv)

    def config_problem(self):
        return self._config_problem

    def read_config(self):
        return dict(self._config)

    def effective_config(self, user=None):
        return dict(self._config)

    def old_unit_dropin_path(self, rec):
        return self._dropin

    def foreign_gateway_home(self):
        return self._foreign_gateway_home

    def legacy_gateway_units(self):
        return self._legacy_gateway_units

    def migrated_webapp_settings(self, values):
        if self._migrated_webapp is not None:
            return self._migrated_webapp
        return SimpleNamespace(enabled=True, host="0.0.0.0", port=_PORT,
                               public_url=None, reason=None)

    def gateway_env_dropin_path(self, name):
        return str(Path(self.home) / name)

    def proposed_webapp_reason(self, host, port, public_url):
        return None


class ApplyHost:
    """The machine behind an apply: real files in a temp home, stubbed services.

    Follows ``tests/thor_cli/test_gateway_migrate_backends_apply.py``'s
    ``FakeHost``; ``now`` is the real clock (the committed fixtures carry real
    timestamps) and ``sleep`` is real, so a failing rollback verify waits out
    its window instead of spinning.
    """

    def __init__(self, home: Path, *, turns=0, old_unit_active=True, bundle=None,
                 gateway_pid=None, pid_listens=False, gateway_status=None,
                 backends=None, old_start_pid=4321):
        self.home = Path(home)
        self.calls: list[str] = []
        self.turns = turns
        self._old_unit_active = old_unit_active
        self._bundle = bundle
        self._gateway_pid = gateway_pid
        self._pid_listens = pid_listens
        self.gateway_status_value = gateway_status if gateway_status is not None else {
            "gateway_state": "running", "auth_required": False, "auth_providers": []}
        self._backends = backends if backends is not None else []
        self._old_start_pid = old_start_pid
        self.gateway = {"installed": False, "enabled": False, "active": False,
                        "running_pid": None, "kind": "systemd", "unit": "thor-gateway"}

    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def read_config(self) -> dict:
        return {}

    def process_env(self, pid):
        return {}

    def backends(self):
        return list(self._backends)

    def start_time(self, pid):
        return 1000 + pid if pid else None

    def same_process(self, pid, start):
        return False

    def running_turns(self, pid, start):
        return self.turns

    def unknown_turn_files(self, pid, start):
        return []

    def gateway_state(self):
        return dict(self.gateway)

    def gateway_status(self, host, port):
        return None if self.gateway_status_value is None else dict(self.gateway_status_value)

    def webapp_page_problem(self, host, port):
        return None

    def gateway_pid(self):
        return self._gateway_pid

    def pid_listens_on(self, pid, port):
        return self._pid_listens

    def port_in_use(self, host, port):
        return False

    def gateway_listens(self, port):
        return False

    def http_status(self, host, port):
        return {"health": "ok", "auth_required": False, "auth_providers": []}

    def old_unit_active(self, rec):
        return self._old_unit_active

    def old_stop(self, rec):
        self.calls.append("old_stop")

    def old_disable(self, rec):
        self.calls.append("old_disable")

    def old_unit_dropin_path(self, rec):
        return None

    def write_old_unit_dropin(self, path):
        self.calls.append("write_old_unit_dropin")

    def remove_old_unit_dropin(self, path):
        self.calls.append("remove_old_unit_dropin")

    def old_enable(self, rec):
        self.calls.append("old_enable")

    def old_start(self, rec, env, argv):
        self.calls.append("old_start")
        return self._old_start_pid

    def live_manual_backend(self, port):
        return None

    def install_gateway(self):
        self.gateway.update(installed=True, enabled=True)
        self.calls.append("install_gateway")

    _VERB_EFFECTS = {"start": ("active", True), "restart": ("active", True),
                     "stop": ("active", False), "enable": ("enabled", True),
                     "disable": ("enabled", False)}

    def gateway_verb(self, verb):
        self.calls.append(f"gateway:{verb}")
        if (effect := self._VERB_EFFECTS.get(verb)) is not None:
            self.gateway[effect[0]] = effect[1]

    def uninstall_gateway(self):
        self.gateway.update(installed=False, enabled=False, active=False)
        self.calls.append("uninstall_gateway")

    def linger(self):
        return None

    def set_linger(self, value):
        self.calls.append(f"linger:{value}")

    def build_bundle(self):
        self.calls.append("build_bundle")

    def bundle_missing(self):
        return self._bundle

    def _write_checked(self, path: Path, text: str, expect) -> bytes:
        current = _digest(path)
        if expect is not None and current != expect:
            raise FileChangedSinceBackup(f"{path.name} changed since the backup")
        path.write_text(text, encoding="utf-8")
        return path.read_bytes()

    def set_config(self, values: dict, *, expect):
        lines = ["webapp:"]
        for key, value in values.items():
            name = key.split(".", 1)[1]
            lines.append(f"  {name}: {value if not isinstance(value, bool) else str(value).lower()}")
        return self._write_checked(self.home / "config.yaml", "\n".join(lines) + "\n", expect)

    def set_env(self, values: dict, *, expect=False):
        path = self.home / ".env"
        lines = [f"{key}={value}" for key, value in values.items()]
        return self._write_checked(path, "\n".join(lines) + "\n",
                                   expect if expect is not False else None)

    def legacy_environment_lines(self, unit):
        return []

    def remove_legacy_units(self):
        self.calls.append("remove_legacy_units")

    def gateway_env_dropin_path(self, name):
        return str(self.home / name)

    def write_gateway_env_dropin(self, path, lines):
        self.calls.append("write_gateway_env_dropin")

    def remove_gateway_env_dropin(self, path):
        self.calls.append("remove_gateway_env_dropin")

    def restore_legacy_unit(self, unit):
        self.calls.append("restore_legacy_unit")

    def foreign_gateway_home(self):
        return None

    def legacy_gateway_units(self):
        return []

    def own_unit(self):
        return None

    def migrated_webapp_settings(self, writes):
        return SimpleNamespace(enabled=True, host="127.0.0.1", port=_PORT,
                               public_url=None, reason=None)

    def gateway_kind(self):
        return "systemd"

    def stop_stray_gateway(self):
        return None

# ---------------------------------------------------------------------------
# Plan payloads (the real dashboard routes, via TestClient)
# ---------------------------------------------------------------------------

def _plan_body(capture: Capture, home: Path, host_kw: dict, *,
               force_interrupt: bool = False) -> dict:
    """GET /api/gateway/migrate/backends/plan for *home* (the route's own JSON)."""
    from thor_cli import web_server
    from thor_cli.web_routers import backend_migration as routes

    routes._SCANS.clear()  # one probe per home: never reuse an earlier probe's scan
    client = capture.client(lambda h: PlanHost(h, **host_kw))
    params = {"force_interrupt": "true"} if force_interrupt else {}
    response = client.get("/api/gateway/migrate/backends/plan", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _status_body(capture: Capture, home: Path, host=None) -> dict:
    """GET /api/gateway/migrate/backends/status for *home* (the route's own JSON)."""
    client = capture.client(lambda h: host if host is not None else PlanHost(h))
    response = client.get("/api/gateway/migrate/backends/status")
    assert response.status_code == 200, response.text
    return response.json()


def _route_scenario(capture: Capture, home: Path):
    """The route scenarios' shell: this home is the default profile's root."""
    capture.setenv("THOR_HOME", str(home))
    original = plan_mod._is_standard_root
    plan_mod._is_standard_root = lambda root: True
    return original


def capture_plans(capture: Capture) -> dict[str, object]:
    """The plan payloads: container and systemd-system backends, held and forced."""
    out: dict[str, object] = {}
    for supervisor, scope, key, running_name, unknown_name in (
            ("container", "user", "containerPlans", "container-running", "container-unknown"),
            ("systemd", "system", "systemSystemdPlans", "system-running", "system-unknown")):
        home = capture.home(running_name)
        original = _route_scenario(capture, home)
        try:
            host_kw = {"items": [_item(home, supervisor=supervisor, scope=scope)], "turns": 1}
            if supervisor == "container":
                # Seen from the host: its Thor version cannot be checked.
                host_kw["same_ns"] = False
            else:
                # A system unit's launcher environment carries the auth keys.
                host_kw["unit_launcher_env"] = _AUTH_ENV
            held = _plan_body(capture, home, host_kw)
            unknown_home = capture.home(unknown_name)
            capture.setenv("THOR_HOME", str(unknown_home))
            unknown_kw = {"items": [_item(unknown_home, supervisor=supervisor, scope=scope)],
                          "turns": None,
                          "unknown_turn_files": [str(unknown_home / "desktop" / "interrupted_turns.json")]}
            if supervisor == "container":
                unknown_kw["same_ns"] = False
            else:
                unknown_kw["unit_launcher_env"] = _AUTH_ENV
            unknown_held = _plan_body(capture, unknown_home, unknown_kw)
            capture.setenv("THOR_HOME", str(home))
            forced = _plan_body(capture, home, host_kw, force_interrupt=True)
            capture.setenv("THOR_HOME", str(unknown_home))
            unknown_forced = _plan_body(capture, unknown_home, unknown_kw, force_interrupt=True)
        finally:
            plan_mod._is_standard_root = original
        out[key] = {"running": {"held": held, "forced": forced},
                    "unknown": {"held": unknown_held, "forced": unknown_forced}}
    return out


def capture_refused_url(capture: Capture) -> dict[str, object]:
    """A systemd SYSTEM unit whose public URL the gateway refuses, held and forced."""
    home = capture.home("refused-url")
    original = _route_scenario(capture, home)
    try:
        host_kw = {"items": [_item(home, supervisor="systemd", scope="system")],
                   # ftp:// counts as unset; a query string normalises but is refused.
                   "config": {"dashboard": {"public_url": "https://thor.example/?x=1"}}}
        held = _plan_body(capture, home, host_kw)
        forced = _plan_body(capture, home, host_kw, force_interrupt=True)
    finally:
        plan_mod._is_standard_root = original
    return {"held": held, "forced": forced}


def capture_plan_while_running(capture: Capture) -> dict:
    """The plan route while a migration is live (a ``running`` manifest, live pid)."""
    home = capture.home("plan-while-running")
    original = _route_scenario(capture, home)
    try:
        # The launcher's auth keys are copied (names only); the route host is
        # told the run is alive, since PlanHost.start_time is stubbed
        # (1000 + pid) and would otherwise read this live pid as dead.
        host = PlanHost(home, items=[_item(home, supervisor="systemd", scope="user")],
                        turns=0, linger=True, process_env=_AUTH_ENV)
        plan = plan_mod.build_plan(host)
        manifest = apply_mod.new_manifest(plan, host)
        manifest["steps"] = [{"name": name, "state": state} for name, state in
                             (("preflight", "done"), ("manifest", "done"),
                              ("webapp_bundle", "done"), ("write_config", "done"),
                              ("gateway_service", "running"), ("stop_old_backend", "done"),
                              ("start_gateway", "pending"), ("verify", "pending"))]
        manifest["step"] = "gateway_service"
        manifest["entered"] = ["preflight", "manifest", "webapp_bundle", "write_config",
                               "gateway_service", "stop_old_backend"]
        manifest["pid"] = os.getpid()  # this process: the run reads as live
        apply_mod.write_manifest(home, manifest)
        return _plan_body(capture, home, {"items": [_item(home, supervisor="systemd", scope="user")],
                                          "turns": 0, "linger": True,
                                          "process_env": _AUTH_ENV,
                                          "same_process_value": True})
    finally:
        plan_mod._is_standard_root = original


# ---------------------------------------------------------------------------
# Blocker strings (the plan, plus the apply path's own refusals)
# ---------------------------------------------------------------------------

def _owner_plan_blockers(capture: Capture, home: Path, host_kw: dict) -> list[str]:
    """The blockers the apply path adds to a movable backend's plan."""
    from thor_cli.web_routers import backend_migration as routes

    host = PlanHost(home, **host_kw)
    return routes._build_plan(host, routes.ApplyBody()).blockers


def capture_refusal_blockers(capture: Capture) -> dict[str, str]:
    """The four refusal blockers: config backend, providers, managed, guard."""
    out: dict[str, str] = {}
    # A non-file config backend: read from this process's environment.
    home = capture.home("refuse-config-backend")
    capture.setenv("THOR_CONFIG_BACKEND", "remote")
    try:
        out["configBackend"] = _owner_plan_blockers(
            capture, home, {"items": [_item(home, supervisor="systemd", scope="user")]})[0]
    finally:
        capture.setenv("THOR_CONFIG_BACKEND", None)
    # Sign-in required, but its providers cannot be read.
    home = capture.home("refuse-providers")
    blockers = _owner_plan_blockers(
        capture, home, {"items": [_item(home, supervisor="systemd", scope="user")],
                        "http": {"health": "ok", "auth_required": True, "auth_providers": None},
                        "health": {"health": "ok", "auth_required": True, "auth_providers": None}})
    out["providers"] = next(b for b in blockers if b.startswith("The old backend requires sign-in"))
    # A managed config that would override the move's webapp.* writes.
    from thor_cli import managed_scope

    home = capture.home("managed")
    old_load, old_dir = managed_scope.load_managed_config, managed_scope.get_managed_dir
    managed_scope.load_managed_config = lambda: {"webapp": {"port": 8000}}
    managed_scope.get_managed_dir = lambda: home  # a Path: _load_managed_file joins it
    try:
        blockers = _owner_plan_blockers(
            capture, home, {"items": [_item(home, supervisor="systemd", scope="user")],
                            "migrated_webapp": SimpleNamespace(enabled=True, host="0.0.0.0",
                                                              port=8000, public_url=None, reason=None)})
    finally:
        managed_scope.load_managed_config, managed_scope.get_managed_dir = old_load, old_dir
    out["managed"] = next(b for b in blockers if b.startswith("The managed config"))
    # The restart guard of the old unit already exists.
    home = capture.home("refuse-guard")
    dropin = home / "systemd-user" / "thor-dashboard.service.d" / "thor-migrated.conf"
    dropin.parent.mkdir(parents=True, exist_ok=True)
    dropin.write_text("", encoding="utf-8")
    blockers = _owner_plan_blockers(
        capture, home, {"items": [_item(home, supervisor="systemd", scope="user")],
                        "dropin": str(dropin)})
    out["guardPath"] = next(b for b in blockers if b.endswith("move it aside before migrating this backend."))
    return out


def capture_unknown_activity_blocker(capture: Capture) -> str:
    """A movable backend whose turn activity cannot be read."""
    home = capture.home("unknown-activity")
    host = PlanHost(home, items=[_item(home, supervisor="systemd", scope="user")],
                    turns=None,
                    unknown_turn_files=[str(home / "desktop" / "interrupted_turns.json")])
    plan = plan_mod.build_plan(host)
    return next(b for b in plan.blockers if b.startswith("Cannot tell whether turns are running"))


def capture_flag_in_path_blockers(capture: Capture) -> dict[str, str]:
    """Blockers for a home whose path itself holds a flag-like component."""
    weird = capture.root / "--force-interrupt/, then re-run with --force-interrupt (any running turn is interrupted)."
    home = weird / "h"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(_CONFIG_BEFORE, encoding="utf-8")
    (home / ".env").write_text(_ENV_BEFORE, encoding="utf-8")
    target = home / "config-real.yaml"
    target.write_text(_CONFIG_BEFORE, encoding="utf-8")
    (home / "config.yaml").unlink()
    (home / "config.yaml").symlink_to(target)
    host = PlanHost(home, items=[_item(home, supervisor="systemd", scope="user")],
                    turns=None,
                    unknown_turn_files=[str(home / "desktop" / "interrupted_turns.json")])
    from thor_cli.web_routers import backend_migration as routes

    plan = routes._build_plan(host, routes.ApplyBody())
    symlink = next(b for b in plan.blockers if "is a symbolic link" in b)
    unknown = next(b for b in plan.blockers if b.startswith("Cannot tell whether turns are running"))
    return {"symlink": symlink, "unknown": unknown}

# ---------------------------------------------------------------------------
# Apply / status payloads (the real engine, then the real status route)
# ---------------------------------------------------------------------------

def _rec(home: Path, *, supervisor: str = "systemd", was_active: bool = True,
         cwd: str | None = None) -> dict:
    """The plan's record of the old backend (as ``_record`` shapes it)."""
    rec = {"supervisor": supervisor, "report_supervisor": supervisor,
           "unit": "thor-dashboard.service", "scope": "user",
           "unit_path": "/home/u/.config/systemd/user/thor-dashboard.service",
           "unit_file_state": "enabled", "was_active": was_active,
           "was_loaded": was_active, "pid": _PID, "start_time": _START,
           "running": was_active, "thor_home": str(home), "this_home": True}
    if supervisor == "manual":
        rec.update(scope=None, unit_path=None, cwd=cwd)
    return rec


def _apply_plan(home: Path, *, supervisor: str = "systemd", was_active: bool = True,
                old_argv: list[str] | None = None, cwd: str | None = None) -> plan_mod.BackendPlan:
    """A movable backend's plan, by hand (as the apply tests build it)."""
    plan = plan_mod.BackendPlan(
        home=str(home), rec=_rec(home, supervisor=supervisor, was_active=was_active, cwd=cwd),
        old_host="0.0.0.0", old_port=_PORT, new_host="0.0.0.0", new_port=_PORT,
        gateway={"installed": False, "enabled": False, "active": False, "running_pid": None,
                 "kind": "systemd", "unit": "thor-gateway"},
        linger=None, auth_before=None, carry={}, generate_secret=False, keep_webapp=False)
    plan.old_argv = old_argv if old_argv is not None else ["/usr/bin/thor", "dashboard", "--no-open",
                                                          "--host", "0.0.0.0", "--port", str(_PORT)]
    return plan


def _quiet(fn, *args, **kwargs):
    """Run *fn* with its progress prints swallowed (the capture reports, not the engine)."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def _standard_root(capture: Capture, home: Path):
    """The status route's shell: this home is the default profile's root."""
    capture.setenv("THOR_HOME", str(home))
    original = plan_mod._is_standard_root
    plan_mod._is_standard_root = lambda root: True
    return original


def capture_relative_launcher_status(capture: Capture) -> dict:
    """A detached apply refused: the old backend's relative launcher cannot be re-read."""
    home = capture.home("relative-launcher")
    host = ApplyHost(home)
    plan = _apply_plan(home, supervisor="manual", cwd=None,
                       old_argv=["./thor", "dashboard", "--host", "0.0.0.0", "--port", str(_PORT)])
    assert _quiet(apply_mod.apply, host, plan, detached=True) == apply_mod.EXIT_BLOCKED
    original = _standard_root(capture, home)
    try:
        return _status_body(capture, home)
    finally:
        plan_mod._is_standard_root = original


def _gateway_service_failure(capture: Capture, name: str, *, turns, backends) -> dict:
    """A real apply that fails at ``gateway_service`` and rolls back (exit 4)."""
    home = capture.home(name)
    host = ApplyHost(home, turns=turns, backends=backends, gateway_pid=None)
    plan = _apply_plan(home)
    assert _quiet(apply_mod.apply, host, plan) == apply_mod.EXIT_ROLLED_BACK
    original = _standard_root(capture, home)
    try:
        return _status_body(capture, home)
    finally:
        plan_mod._is_standard_root = original


def capture_late_turn_status(capture: Capture) -> dict[str, dict]:
    """A turn starts (or its activity turns unreadable) after the preflight."""
    running_item = _item(capture.root / "late-turn-running", supervisor="systemd", scope="user")
    running = _gateway_service_failure(capture, "late-turn-running", turns=1, backends=[running_item])
    unknown_item = _item(capture.root / "late-turn-unknown", supervisor="systemd", scope="user")
    unknown = _gateway_service_failure(capture, "late-turn-unknown", turns=None, backends=[unknown_item])
    return {"running": running, "unknown": unknown}


def capture_changed_backend_status(capture: Capture) -> dict:
    """The old backend is replaced between the check and the stop."""
    home = capture.home("changed-backend")
    changed = _item(home, supervisor="systemd", scope="user", pid=5242)
    host = ApplyHost(home, backends=[changed], gateway_pid=None)
    plan = _apply_plan(home)
    assert _quiet(apply_mod.apply, host, plan) == apply_mod.EXIT_ROLLED_BACK
    original = _standard_root(capture, home)
    try:
        return _status_body(capture, home)
    finally:
        plan_mod._is_standard_root = original


def _crafted_manifest(capture: Capture, name: str, *, supervisor: str, was_active: bool = True,
                      step: str, steps: list[tuple[str, str]], entered: list[str],
                      files_after_apply: dict | None = None, cwd: str | None = None,
                      old_argv: list[str] | None = None) -> tuple[Path, ApplyHost, dict]:
    """A manifest built by the real ``new_manifest``, then edited into the interrupted shape."""
    home = capture.home(name)
    host = ApplyHost(home)
    plan = _apply_plan(home, supervisor=supervisor, was_active=was_active,
                       old_argv=old_argv, cwd=cwd if cwd is not None else (str(home) if supervisor == "manual" else None))
    manifest = apply_mod.new_manifest(plan, host)
    manifest["step"] = step
    manifest["steps"] = [{"name": n, "state": s} for n, s in steps]
    manifest["entered"] = list(entered)
    manifest["pid"] = 999999  # dead: the next run rolls it back instead of resuming it
    manifest["pid_start_time"] = 12345
    if files_after_apply is not None:
        manifest["files_after_apply"] = dict(files_after_apply)
    apply_mod.write_manifest(home, manifest)
    return home, host, manifest


def capture_killed_while_writing_status(capture: Capture) -> dict[str, dict]:
    """A run killed mid-write: the file it was writing is not put back (exit 5)."""
    out: dict[str, dict] = {}
    for key, name, writing in (("config", "config.yaml", "config.yaml"),
                               ("env", ".env", ".env")):
        home = capture.home(f"killed-{key}")
        host = ApplyHost(home)
        plan = _apply_plan(home)
        manifest = apply_mod.new_manifest(plan, host)
        # The run was writing this file when it died: its content is the
        # migration's (it differs from the backup) and its record says "writing".
        target = home / writing
        if writing == "config.yaml":
            target.write_text("webapp:\n  enabled: true\n  host: 0.0.0.0\n  port: 9119\n", encoding="utf-8")
        else:
            target.write_text(_ENV_BEFORE + "THOR_DASHBOARD_BASIC_AUTH_PASSWORD=changed-while-writing\n",
                              encoding="utf-8")
        backups = manifest["backups"]
        files_after_apply = {n: _digest(Path(backups[k])) for k, n in
                             (("config", "config.yaml"), ("env", ".env"))}
        files_after_apply[writing] = "writing"
        manifest["step"] = "write_config"
        manifest["steps"] = [{"name": n, "state": s} for n, s in
                             (("preflight", "done"), ("manifest", "done"),
                              ("webapp_bundle", "done"), ("write_config", "done"),
                              ("gateway_service", "pending"), ("stop_old_backend", "pending"),
                              ("start_gateway", "pending"), ("verify", "pending"))]
        manifest["entered"] = ["preflight", "manifest", "webapp_bundle", "write_config",
                               "stop_old_backend"]
        manifest["pid"] = 999999
        manifest["pid_start_time"] = 12345
        manifest["files_after_apply"] = files_after_apply
        apply_mod.write_manifest(home, manifest)
        assert _quiet(apply_mod.recover_interrupted, host, manifest) == apply_mod.EXIT_ROLLBACK_INCOMPLETE
        original = _standard_root(capture, home)
        try:
            out[key] = _status_body(capture, home)
        finally:
            plan_mod._is_standard_root = original
    return out


def capture_restore_refused_status(capture: Capture) -> dict[str, dict]:
    """A finished migration whose backups are gone: ``--restore`` refuses (exit 3)."""
    out: dict[str, dict] = {}
    for key, missing in (("envMissing", ("env",)), ("configMissing", ("config",)),
                         ("bothMissing", ("config", "env"))):
        home = capture.home(f"restore-{key}")
        # The unchanged pid-4242 item: _changed_since_check reads it back
        # before the stop, and the gateway pid must listen for the verify.
        host = ApplyHost(home, gateway_pid=1234, pid_listens=True,
                         backends=[_item(home, supervisor="systemd", scope="user")])
        plan = _apply_plan(home)
        assert _quiet(apply_mod.apply, host, plan) == apply_mod.EXIT_OK
        manifest = apply_mod.read_manifest(home)
        assert manifest is not None and manifest["state"] == "done"
        for backup_key in missing:
            Path(manifest["backups"][backup_key]).unlink()
        original = _standard_root(capture, home)
        try:
            assert _quiet(apply_mod.restore, host, yes=True, detached=True) == apply_mod.EXIT_BLOCKED
            out[key] = _status_body(capture, home)
        finally:
            plan_mod._is_standard_root = original
    return out


def capture_unknown_state_status(capture: Capture) -> dict:
    """A migration record whose state no run knows."""
    home = capture.home("unknown-state")
    manifest = {"version": 1, "kind": "apply", "state": "bogus", "step": "", "message": "",
                "steps": [], "entered": [], "old_address": "", "new_address": "",
                "dial": {"host": "127.0.0.1", "old_host": "127.0.0.1", "verify_hosts": ["127.0.0.1"],
                         "old_port": _PORT, "new_port": _PORT},
                "started_at": 0.0, "finished_at": None, "pid": 999999, "pid_start_time": 12345,
                "backups": {}, "old_backend": {}, "gateway": {}, "linger": None}
    apply_mod.write_manifest(home, manifest)
    original = _standard_root(capture, home)
    try:
        return _status_body(capture, home)
    finally:
        plan_mod._is_standard_root = original


def capture_exit5_bundle_status(capture: Capture) -> dict[str, dict]:
    """A run that failed at the Webapp bundle and whose old backend stays down (exit 5)."""
    out: dict[str, dict] = {}
    for key, supervisor in (("systemd", "systemd"), ("manual", "manual")):
        home, host, manifest = _crafted_manifest(
            capture, f"exit5-{key}", supervisor=supervisor, step="webapp_bundle",
            steps=[("preflight", "done"), ("manifest", "done"), ("webapp_bundle", "done"),
                   ("write_config", "pending"), ("gateway_service", "pending"),
                   ("stop_old_backend", "pending"), ("start_gateway", "pending"),
                   ("verify", "pending")],
            entered=["preflight", "manifest", "webapp_bundle", "stop_old_backend"])
        host._old_unit_active = False  # the old backend is not verified afterwards
        host._bundle = "dist/index.html is missing"
        run = apply_mod.Run(host, manifest)
        reason = (f"webapp_bundle failed: the Webapp bundle is still missing after the build: "
                  f"{host.bundle_missing()}")
        assert _quiet(apply_mod.rollback, host, run, reason=reason) == apply_mod.EXIT_ROLLBACK_INCOMPLETE
        original = _standard_root(capture, home)
        try:
            out[key] = _status_body(capture, home)
        finally:
            plan_mod._is_standard_root = original
    return out


def capture_non_file_backend_apply(capture: Capture) -> dict[str, dict]:
    """The apply route's two non-file-config-backend answers: precheck and launcher."""
    from thor_cli.web_routers import backend_migration as routes
    from thor_cli import web_server_gateway

    home = capture.home("non-file-backend")
    original = _standard_root(capture, home)
    try:
        host_kw = {"items": [_item(home, supervisor="systemd", scope="user")]}
        # Precheck: the route's own plan is blocked by the config backend.
        capture.setenv("THOR_CONFIG_BACKEND", "remote")
        try:
            client = capture.client(lambda h: PlanHost(h, **host_kw))
            precheck = client.post("/api/gateway/migrate/backends/apply", json={})
        finally:
            capture.setenv("THOR_CONFIG_BACKEND", None)
        assert precheck.status_code == 409, precheck.text
        # Launcher: the route's plan passes, but the detached run refuses.
        capture.setenv("THOR_CONFIG_BACKEND", "remote")
        try:
            message = apply_mod._non_file_config_backend()
        finally:
            capture.setenv("THOR_CONFIG_BACKEND", None)
        assert message is not None

        def record(subcommand, name, *, env_overrides=None, output=None):
            line = {"detached": False, "mode": "apply", "outcome": "refused", "message": message}
            output.write(f"{json.dumps(line)}\n".encode())
            # The refused launcher exits 3, as the real one does.
            return SimpleNamespace(pid=777, poll=lambda: 3, wait=lambda timeout=None: 3)

        real_spawn = web_server_gateway._spawn_thor_action
        web_server_gateway._spawn_thor_action = record
        try:
            client = capture.client(lambda h: PlanHost(h, **host_kw))
            launched = client.post("/api/gateway/migrate/backends/apply", json={})
        finally:
            web_server_gateway._spawn_thor_action = real_spawn
        assert launched.status_code == 409, launched.text
        return {"precheck": precheck.json(), "launcher": launched.json()}
    finally:
        plan_mod._is_standard_root = original


# ---------------------------------------------------------------------------
# engineStepStrings: probe homes
#
# No main scenario produces a step string whose home is a probe home, so
# engineStepStrings is collected entirely from by-hand probes over five
# homes: probe/home, probe/x h and probe/w h (real directories under the
# capture root) plus /h and C:/Users/u/.thor (literal path strings, never
# created on disk). The probes exercise the same code the payloads do, in
# three modes:
#   raw      direct build_plan(); the command is pinned, "THOR_HOME=<home> thor ..."
#   standard THOR_HOME is the probe home and _is_standard_root is patched,
#            so the command is bare "thor -p default ..."
#   route    GET /plan with THOR_HOME=home: the route's _plan_view qualifies
#            the raw steps, "THOR_HOME=<home> thor -p default ..." (posix)
#            or "$env:THOR_HOME='<home>'; thor -p default ..." (windows)
# Windows probes run through the route (or direct build_plan + qualify()),
# because their $env pin only exists in the qualified view. _file_step() is
# probed directly for every state, and _manual_rollback_steps() for every
# supervisor shape. Each collected string is tagged with its provenance so a
# divergence can be traced back to the probe that produced it.
# ---------------------------------------------------------------------------

_PROBE_URL = "https://thor.example/"
_STARTUP_LNK = "C:\\Users\\u\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Thor Dashboard.lnk"
_LAUNCHD_PATH = "/Users/u/Library/LaunchAgents/ai.thor.dashboard.plist"
_SYSTEMD_UNIT_PATH = "/home/u/.config/systemd/user/thor-dashboard.service"
_DROPIN_PATH = "/home/u/.config/systemd/user/thor-dashboard.service.d/thor-migrated.conf"


def _probe_item(home, supervisor="systemd", scope="system", bind="127.0.0.1", *,
                unit="thor-dashboard.service", unit_path=None, pid=_PID,
                state="enabled", argv=None):
    """A by-hand probe backend: systemd SYSTEM scope, so the plan is unsupported.

    A systemd USER unit is movable, not unsupported, and a manual backend is
    movable too, so neither yields plan steps; their stop lines come from
    direct manual_steps() probes below instead. *argv* overrides the command
    line: ``[]`` is the unknown-address case (no --host/--port is the default
    127.0.0.1:9119, not unknown)."""
    argv = ["/usr/bin/thor", "dashboard"] if bind is None else \
        ["/usr/bin/thor", "dashboard", "--host", bind, "--port", "9119"] \
        if argv is None else argv
    return BackendItem(supervisor=supervisor, scope=scope, running=True, pid=pid,
                       unit=unit, unit_path=unit_path, state=state,
                       thor_home=str(home), this_home=True, argv=argv)


def _plan_probe(capture: Capture, home, host_kw: dict, *, mode="raw",
                force_interrupt: bool = True) -> list[str]:
    """The unsupported steps of one by-hand plan probe (see the header above)."""
    from thor_cli.web_routers import backend_migration as routes

    if mode == "route":
        capture.setenv("THOR_HOME", str(home))
        body = _plan_body(capture, home, host_kw, force_interrupt=force_interrupt)
        return [s for entry in body["plan"]["unsupported"] for s in entry["steps"]]
    if mode == "standard":
        capture.setenv("THOR_HOME", str(home))
        original = plan_mod._is_standard_root
        plan_mod._is_standard_root = lambda root: True
    else:
        capture.setenv("THOR_HOME", str(capture.root))  # neutral: the probe home is pinned
        original = None
    try:
        host = PlanHost(home, **host_kw)
        plan = plan_mod.build_plan(host, force_interrupt=force_interrupt)
        return [s for _i, _t, steps in plan.unsupported for s in steps]
    finally:
        if original is not None:
            plan_mod._is_standard_root = original


def _qualified_probe(capture: Capture, home, host_kw: dict, *,
                     force_interrupt: bool = True) -> list[str]:
    """The same probe, passed through the route's qualify() (windows + x h)."""
    from thor_cli.web_routers import backend_migration as routes

    capture.setenv("THOR_HOME", str(capture.root))
    host = PlanHost(home, **host_kw)
    plan = plan_mod.build_plan(host, force_interrupt=force_interrupt)
    raw = [s for _i, _t, steps in plan.unsupported for s in steps]
    return routes.qualify(raw, "default")


def _rollback_manifest(home_s: str, *, supervisor="systemd", scope="user",
                       unit="thor-dashboard.service", unit_path=None,
                       unit_file_state="enabled", was_active=True, pid=_PID,
                       gateway_installed=False, gateway_active=False,
                       files_put_back=None, files_after_apply=None,
                       backups=None, old_unit_dropin=None):
    """A hand-made manifest in new_manifest()'s shape for _manual_rollback_steps().

    "stop_old_backend" is in entered: without it _old_never_stopped() returns
    True and the supervisor's re-enable/restart lines are never emitted.
    """
    if backups is None:
        backups = {"config": f"{home_s}/backend_migration/config.yaml.bak",
                   "env": f"{home_s}/backend_migration/env.bak",
                   "launcher_env": None, "config_mode": 0o644, "env_mode": 0o600}
    return {"version": 1, "kind": "apply", "state": "failed", "step": "write_config",
            "message": "", "steps": [], "entered": ["preflight", "manifest", "stop_old_backend"],
            "old_address": "0.0.0.0:9119", "new_address": "0.0.0.0:9119",
            "dial": {"host": "127.0.0.1", "old_host": "127.0.0.1",
                     "verify_hosts": ["127.0.0.1"], "old_port": _PORT, "new_port": _PORT},
            "started_at": 0.0, "finished_at": None, "pid": 999999, "pid_start_time": 12345,
            "backups": backups,
            "old_backend": {"supervisor": supervisor, "scope": scope, "kind": "dashboard",
                            "profile": "default", "pid": pid, "start_time": 0.0,
                            "unit": unit, "unit_path": unit_path, "state": unit_file_state,
                            "unit_file_state": unit_file_state, "home": home_s,
                            "argv": ["/usr/bin/thor", "dashboard", "--host", "0.0.0.0",
                                     "--port", "9119"],
                            "env_keys": (), "run_count": 1,
                            "service_state": unit_file_state, "enabled": True,
                            "was_active": was_active},
            "old_backend_enabled": True,
            "gateway": {"installed": gateway_installed, "enabled": False,
                        "active": gateway_active},
            "linger": None, "webapp_before": None, "auth_before": None, "copied_env_keys": [],
            "keep_webapp_address": False, "files_put_back": files_put_back or {},
            "files_after_apply": files_after_apply or {},
            "old_unit_dropin": old_unit_dropin, "home": home_s}


def _rollback_probe(capture: Capture, home_s: str, *, mode="raw", **kw) -> list[str]:
    """_manual_rollback_steps() for a hand-made manifest (raw or standard mode)."""
    if mode == "standard":
        capture.setenv("THOR_HOME", home_s)
        original = plan_mod._is_standard_root
        plan_mod._is_standard_root = lambda root: True
    else:
        capture.setenv("THOR_HOME", str(capture.root))
        original = None
    try:
        return apply_mod._manual_rollback_steps(_rollback_manifest(home_s, **kw))
    finally:
        if original is not None:
            plan_mod._is_standard_root = original


def capture_engine_step_strings(capture: Capture) -> list[str]:
    """Every step string the engine can print, over the five probe homes."""
    from thor_cli.web_routers import backend_migration as routes

    seen: dict[str, str] = {}

    def add(strings, provenance):
        for s in strings:
            seen.setdefault(s, provenance)

    root = capture.root
    ph = root / "probe" / "home"
    px = root / "probe" / "x h"
    pw = root / "probe" / "w h"
    slash_h = "/h"
    c_home = "C:/Users/u/.thor"
    for name in ("probe/home", "probe/x h", "probe/w h"):
        capture.home(name)
    # The cp variant of _file_step reads the backup files: keep real ones.
    bak = ph / "backend_migration"
    bak.mkdir(parents=True, exist_ok=True)
    (bak / "config.yaml.bak").write_text(_CONFIG_BEFORE, encoding="utf-8")
    (bak / "env.bak").write_text(_ENV_BEFORE, encoding="utf-8")
    auth = {"unit_launcher_env": _AUTH_ENV, "process_env": _AUTH_ENV}

    # --- probe/home: plain posix probes, raw + standard -------------------
    systemd_keys = {"items": [_probe_item(ph)], **auth}
    systemd_plain = {"items": [_probe_item(ph)]}
    add(_plan_probe(capture, ph, systemd_keys), "probe/home systemd-system 127.0.0.1 keys raw")
    add(_plan_probe(capture, ph, systemd_plain), "probe/home systemd-system 127.0.0.1 no-keys raw")
    add(_plan_probe(capture, ph, {"items": [_probe_item(ph, supervisor="container",
                                                        bind="0.0.0.0")],
                                  "same_ns": False}),
        "probe/home container 0.0.0.0 raw")
    add(_plan_probe(capture, ph, {"items": [_probe_item(ph, supervisor="nix-systemd",
                                                        bind="0.0.0.0")]}),
        "probe/home nix-systemd 0.0.0.0 raw")
    add(_plan_probe(capture, ph, {"items": [_probe_item(ph, supervisor="nix-launchd",
                                                        bind="0.0.0.0")]}),
        "probe/home nix-launchd 0.0.0.0 raw")
    add(_plan_probe(capture, ph, systemd_keys, mode="standard"),
        "probe/home systemd-system 127.0.0.1 keys standard")
    add(_plan_probe(capture, ph, {"items": [_probe_item(ph, bind="0.0.0.0")]},
                    mode="standard"),
        "probe/home systemd-system 0.0.0.0 no-keys standard")
    # No-service: only a movable backend gets the by-hand entry build_plan()
    # appends, so the item is manual (its stop line is the default one) and
    # the gateway kind is None; http answers so the movable checks pass.
    add(_plan_probe(capture, ph,
                    {"items": [_probe_item(ph, supervisor="manual")],
                     "gateway": {"kind": None},
                     "http": {"health": "ok", "auth_required": True,
                              "auth_providers": ["basic"]}},
                    mode="standard"),
        "probe/home no-service manual standard")
    # Direct manual_steps() probes. A manual backend is movable, so no plan
    # yields its stop line; the public-URL lines are hand-made tuples too:
    # resolve_public_url() normalises "https://thor.example/" to
    # "https://thor.example", and an ftp:// value counts as unset.
    capture.setenv("THOR_HOME", str(root))  # neutral: the command is pinned, bare
    add(plan_mod.manual_steps("127.0.0.1", _PORT, _probe_item(ph, supervisor="manual"),
                              env_keys=(), home=str(ph), no_service=False,
                              public_url=None, keep_address=False),
        "probe/home manual_steps manual stop")
    add(plan_mod.manual_steps("127.0.0.1", _PORT, _probe_item(ph), env_keys=(),
                              home=str(ph), no_service=False,
                              public_url=(None, "The old backend's public URL "
                                               "(dashboard.public_url)"),
                              keep_address=False),
        "probe/home manual_steps public-url problem")
    capture.setenv("THOR_HOME", str(ph))  # standard mode for the good-URL line
    original = plan_mod._is_standard_root
    plan_mod._is_standard_root = lambda root: True
    try:
        add(plan_mod.manual_steps("127.0.0.1", _PORT, _probe_item(ph),
                                  env_keys=tuple(sorted(_AUTH_ENV)),
                                  home=str(ph), no_service=False,
                                  public_url=(_PROBE_URL, None), keep_address=False),
            "probe/home manual_steps public-url standard")
    finally:
        plan_mod._is_standard_root = original

    # --- probe/x h: raw + route-qualified ---------------------------------
    add(_plan_probe(capture, px, {"items": [_probe_item(px)], **auth}),
        "probe/x h systemd-system 127.0.0.1 keys raw")
    add(_plan_probe(capture, px, {"items": [_probe_item(px, bind="0.0.0.0")]}),
        "probe/x h systemd-system 0.0.0.0 no-keys raw")
    add(_plan_probe(capture, px, {"items": [_probe_item(px)], **auth}, mode="route"),
        "probe/x h systemd-system 127.0.0.1 keys route")

    # --- probe/w h: windows probes, route-qualified ------------------------
    win_startup = {"items": [_probe_item(pw, supervisor="startup-folder", bind="0.0.0.0",
                                         unit="Thor Dashboard", unit_path=_STARTUP_LNK)],
                   "family": "win32", "process_env": _AUTH_ENV}
    add(_plan_probe(capture, pw, win_startup, mode="route"),
        "probe/w h windows startup-folder 0.0.0.0 route")
    for unit in ("Thor Dashboard", "thor-dashboard.service"):
        add(_qualified_probe(capture, pw,
                             {"items": [_probe_item(pw, supervisor="scheduled-task",
                                                    bind="0.0.0.0", unit=unit)],
                              "family": "win32", "process_env": _AUTH_ENV}),
            f"probe/w h windows scheduled-task {unit}")
    add(_qualified_probe(capture, pw,
                         {"items": [_probe_item(pw, supervisor="manual", bind="0.0.0.0",
                                                pid=None)],
                          "family": "win32", "process_env": _AUTH_ENV}),
        "probe/w h windows manual no-pid")

    # --- C:/Users/u/.thor: windows route + raw posix -----------------------
    win_c = {"items": [_probe_item(c_home, supervisor="startup-folder", bind="0.0.0.0",
                                   unit="thor-dashboard.service",
                                   unit_path=_SYSTEMD_UNIT_PATH)],
             "family": "win32", "process_env": _AUTH_ENV,
             "config": {"dashboard": {"public_url": _PROBE_URL}}}
    add(_plan_probe(capture, c_home, win_c, mode="route"),
        "C: windows startup-folder 0.0.0.0 public-url route")
    add(_plan_probe(capture, c_home,
                    {"items": [_probe_item(c_home, supervisor="startup-folder",
                                           bind="127.0.0.1",
                                           unit="thor-dashboard.service",
                                           unit_path=_SYSTEMD_UNIT_PATH)],
                     "family": "win32", "process_env": _AUTH_ENV,
                     "config": {"dashboard": {"public_url": _PROBE_URL}}},
                    mode="route"),
        "C: windows startup-folder 127.0.0.1 public-url route")
    # The same home with the Startup-folder .lnk entry: only the move lines differ.
    add(_plan_probe(capture, c_home,
                    {"items": [_probe_item(c_home, supervisor="startup-folder",
                                           bind="0.0.0.0",
                                           unit="Thor Dashboard",
                                           unit_path=_STARTUP_LNK)],
                     "family": "win32", "process_env": _AUTH_ENV,
                     "config": {"dashboard": {"public_url": _PROBE_URL}}},
                    mode="route"),
        "C: windows startup-folder lnk 0.0.0.0 public-url route")
    # Unknown address on Windows: an empty command line (no --host/--port is
    # the 127.0.0.1:9119 default, not unknown).
    add(_plan_probe(capture, c_home,
                    {"items": [_probe_item(c_home, supervisor="startup-folder",
                                           unit="Thor Dashboard",
                                           unit_path=_STARTUP_LNK, argv=[])],
                     "family": "win32", "process_env": _AUTH_ENV},
                    mode="route"),
        "C: windows startup-folder unknown-address route")
    add(_plan_probe(capture, c_home, {"items": [_probe_item(c_home)], **auth}),
        "C: systemd-system 127.0.0.1 keys raw posix")
    restored = {"files_put_back": {"config.yaml": "restored", ".env": "restored"}}

    def _missing_backups(home_s):
        return {"backups": {"config": f"{home_s}/backend_migration/config.yaml.bak",
                            "env": f"{home_s}/backend_migration/env.bak",
                            "launcher_env": None, "config_mode": 0o644,
                            "env_mode": 0o600}}

    add(_rollback_probe(capture, c_home, **restored), "C: rollback systemd user restored raw")
    add(_rollback_probe(capture, c_home, **_missing_backups(c_home)),
        "C: rollback systemd user missing raw")

    # --- /h: raw posix probes ---------------------------------------------
    add(_plan_probe(capture, slash_h, {"items": [_probe_item(slash_h)], **auth}),
        "/h systemd-system 127.0.0.1 keys raw")
    add(_plan_probe(capture, slash_h, {"items": [_probe_item(slash_h)]}),
        "/h systemd-system 127.0.0.1 no-keys raw")
    add(_plan_probe(capture, slash_h,
                    {"items": [_probe_item(slash_h, argv=[])], **auth}),
        "/h systemd-system unknown-address raw")
    add(_rollback_probe(capture, slash_h, **restored), "/h rollback systemd user restored raw")
    add(_rollback_probe(capture, slash_h, **_missing_backups(slash_h)),
        "/h rollback systemd user missing raw")

    # --- _file_step, every state, at probe/home ---------------------------
    ph_s = str(ph)
    real_backups = {"config": str(bak / "config.yaml.bak"), "env": str(bak / "env.bak"),
                    "launcher_env": None, "config_mode": 0o644, "env_mode": 0o600}
    gone_backups = {"config": f"{ph_s}/gone.bak", "env": f"{ph_s}/gone-env.bak",
                    "launcher_env": None, "config_mode": 0o644, "env_mode": 0o600}
    no_backups = {"config": None, "env": None, "launcher_env": None,
                  "config_mode": 0o644, "env_mode": 0o600}
    file_cases = {
        "restored": {"backups": real_backups,
                     "files_put_back": {"config.yaml": "restored", ".env": "restored"}},
        "kept-backup": {"backups": real_backups,
                        "files_put_back": {"config.yaml": "kept", ".env": "kept"},
                        "files_after_apply": {"config.yaml": "x" * 64, ".env": "y" * 64}},
        "kept-no-backup": {"backups": no_backups,
                           "files_put_back": {"config.yaml": "kept", ".env": "kept"},
                           "files_after_apply": {"config.yaml": "x" * 64, ".env": "y" * 64}},
        "missing": {"backups": gone_backups},
        "writing": {"backups": real_backups,
                    "files_put_back": {"config.yaml": "kept", ".env": "kept"},
                    "files_after_apply": {"config.yaml": "writing", ".env": "writing"}},
        "cp": {"backups": real_backups},
        "rm": {"backups": no_backups},
    }
    for case, kw in file_cases.items():
        m = _rollback_manifest(ph_s, **kw)
        for key, name in apply_mod._RESTORED_FILES:
            add([apply_mod._file_step(m, ph_s, key, name)],
                f"probe/home _file_step {case} {name}")

    # --- _manual_rollback_steps, every supervisor shape -------------------
    # At /h, so the gateway stop/uninstall and file lines coincide with the
    # /h rollback probes above; only the supervisor lines are new.
    add(_rollback_probe(capture, ph_s, mode="standard", **restored),
        "probe/home rollback systemd user restored standard")
    add(_rollback_probe(capture, ph_s, mode="standard", gateway_installed=True,
                        gateway_active=True, **restored),
        "probe/home rollback systemd user gateway-active standard")
    add(_rollback_probe(capture, slash_h, unit_file_state="enabled-runtime",
                        was_active=False, **restored),
        "/h rollback systemd user enabled-runtime raw")
    add(_rollback_probe(capture, slash_h, scope="system", **restored),
        "/h rollback systemd system restored raw")
    add(_rollback_probe(capture, slash_h, supervisor="launchd", scope="gui/501",
                        unit="ai.thor.dashboard", unit_path=_LAUNCHD_PATH, **restored),
        "/h rollback launchd raw")
    add(_rollback_probe(capture, slash_h, supervisor="manual", **restored),
        "/h rollback manual pid raw")
    add(_rollback_probe(capture, slash_h, supervisor="manual", pid=None, **restored),
        "/h rollback manual no-pid raw")
    add(_rollback_probe(capture, slash_h, old_unit_dropin=_DROPIN_PATH, **restored),
        "/h rollback systemd user dropin raw")
    return sorted(seen)


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

_CAPTURES = (
    ("plans", "capture_plans"),
    ("refused-url", "capture_refused_url"),
    ("plan-while-running", "capture_plan_while_running"),
    ("refusal-blockers", "capture_refusal_blockers"),
    ("unknown-activity", "capture_unknown_activity_blocker"),
    ("flag-in-path", "capture_flag_in_path_blockers"),
    ("relative-launcher", "capture_relative_launcher_status"),
    ("late-turn", "capture_late_turn_status"),
    ("changed-backend", "capture_changed_backend_status"),
    ("killed-while-writing", "capture_killed_while_writing_status"),
    ("restore-refused", "capture_restore_refused_status"),
    ("unknown-state", "capture_unknown_state_status"),
    ("exit5-bundle", "capture_exit5_bundle_status"),
    ("non-file-backend", "capture_non_file_backend_apply"),
    ("engine-steps", "capture_engine_step_strings"),
)

# The fixture files' exports, in the order they are written there.
_ENGINE_EXPORTS = ("unknownActivityBlocker", "refusedUrlPlans", "refusalBlockers",
                   "relativeLauncherStatus", "lateTurnStatus", "killedWhileWritingStatus",
                   "restoreRefusedStatus", "unknownStateStatus", "changedBackendStatus",
                   "nonFileBackendApply", "exit5BundleStatus", "flagInPathBlockers",
                   "engineStepStrings", "planWhileRunning")
_PLANS_EXPORTS = ("containerPlans", "systemSystemdPlans", "refusedUrlPlans")


# Where each capture's value goes: (sink, key) pairs; a None key merges the
# returned dict into the sink. "refused-url" is shared by both fixtures.
_CAPTURE_SINKS = {
    "plans": (("plans", None),),
    "refused-url": (("plans", "refusedUrlPlans"), ("engine", "refusedUrlPlans")),
    "plan-while-running": (("engine", "planWhileRunning"),),
    "refusal-blockers": (("engine", "refusalBlockers"),),
    "unknown-activity": (("engine", "unknownActivityBlocker"),),
    "flag-in-path": (("engine", "flagInPathBlockers"),),
    "relative-launcher": (("engine", "relativeLauncherStatus"),),
    "late-turn": (("engine", "lateTurnStatus"),),
    "changed-backend": (("engine", "changedBackendStatus"),),
    "killed-while-writing": (("engine", "killedWhileWritingStatus"),),
    "restore-refused": (("engine", "restoreRefusedStatus"),),
    "unknown-state": (("engine", "unknownStateStatus"),),
    "exit5-bundle": (("engine", "exit5BundleStatus"),),
    "non-file-backend": (("engine", "nonFileBackendApply"),),
    "engine-steps": (("engine", "engineStepStrings"),),
}


def _assemble(capture: Capture, only: set[str]) -> tuple[dict, dict]:
    """Run the selected captures and return (engine_exports, plans_exports)."""
    plans: dict = {}
    engine: dict = {}
    sinks = {"plans": plans, "engine": engine}
    for name, fn_name in _CAPTURES:
        if name not in only:
            continue
        value = globals()[fn_name](capture)
        for sink, key in _CAPTURE_SINKS[name]:
            if key is None:
                sinks[sink].update(value)
            else:
                sinks[sink][key] = value
    engine = {k: engine[k] for k in _ENGINE_EXPORTS if k in engine}
    plans = {k: plans[k] for k in _PLANS_EXPORTS if k in plans}
    return engine, plans


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", default=True,
                        help="capture and compare against the committed fixtures (default)")
    parser.add_argument("--write", metavar="DIR", default=None,
                        help="write fresh fixtures to DIR instead of comparing")
    parser.add_argument("--force", action="store_true",
                        help="with --write: write even when the capture diverges")
    parser.add_argument("--root", metavar="DIR", default=None,
                        help="capture root (a fresh temp dir by default)")
    parser.add_argument("--keep-root", action="store_true",
                        help="keep the capture root after the run, for debugging")
    parser.add_argument("--only", metavar="NAME", default=None,
                        help="comma-separated capture names to run (see _CAPTURES); "
                             "for fast iteration, e.g. --only engine-steps")
    args = parser.parse_args(argv)
    only = set(_CAPTURES[i][0] for i in range(len(_CAPTURES))) if not args.only else \
        {name.strip() for name in args.only.split(",")}
    unknown = only - {name for name, _fn in _CAPTURES}
    if unknown:
        parser.error(f"unknown capture(s): {', '.join(sorted(unknown))}")
    root = Path(args.root) if args.root else Path(tempfile.mkdtemp(prefix="thor-capture-"))
    capture = Capture(root)
    try:
        engine, plans = _assemble(capture, only)
        engine_text = render_fixture(ENGINE_HEADER, engine)
        plans_text = render_fixture(PLANS_HEADER, plans)
        if args.write:
            out_dir = Path(args.write)
            if not ENGINE_FIXTURE.exists() or not PLANS_FIXTURE.exists():
                print("No committed fixtures to compare against; writing anyway.")
                problems = []
            else:
                problems = compare_fixtures(engine_text, ENGINE_FIXTURE, str(root)) + \
                    compare_fixtures(plans_text, PLANS_FIXTURE, str(root))
            if problems and not args.force:
                print("Capture diverges from the committed fixtures; refusing to write:")
                for problem in problems:
                    print(f"  {problem}")
                return 1
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / ENGINE_FIXTURE.name).write_text(engine_text, encoding="utf-8")
            (out_dir / PLANS_FIXTURE.name).write_text(plans_text, encoding="utf-8")
            print(f"Wrote {out_dir / ENGINE_FIXTURE.name} and {out_dir / PLANS_FIXTURE.name}")
            return 0
        problems = []
        if not ENGINE_FIXTURE.exists():
            print(f"Missing committed fixture: {ENGINE_FIXTURE}")
            problems.append("engine fixture missing")
        else:
            problems += compare_fixtures(engine_text, ENGINE_FIXTURE, str(root),
                                         only=set(engine))
        if not PLANS_FIXTURE.exists():
            print(f"Missing committed fixture: {PLANS_FIXTURE}")
            problems.append("plans fixture missing")
        else:
            problems += compare_fixtures(plans_text, PLANS_FIXTURE, str(root),
                                         only=set(plans))
        if problems:
            print("Capture diverges from the committed fixtures:")
            for problem in problems:
                print(f"  {problem}")
            return 1
        print("Capture matches the committed fixtures.")
        return 0
    finally:
        capture.restore_env()
        if not args.keep_root and not args.root:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
