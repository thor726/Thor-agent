"""End-to-end ``thor gateway migrate --backends`` against a real old backend (Fase 6).

One scenario, real processes only: a ``thor serve`` backend started by hand from a shell
serves a temporary ``THOR_HOME`` on a free port, with basic-auth sign-in active, and the
migration CLI is driven against it as a subprocess. Every verdict below comes from an
HTTP probe of the address, never from a log claim.

What this file automates, and what it deliberately does not:

* Automated here: the report finds the hand-started backend (supervisor, pid, address);
  the dry run plans the same address, names the ``.env`` keys to copy (never their
  values) and changes nothing; a live turn marker blocks the move until it is cleared;
  the update notice names the dry-run command; and a run interrupted after stopping the
  old backend is rolled back by the next ``--apply`` (exit 4) with the old backend
  answering again on its address and ``config.yaml``/``.env`` byte-identical to before.
* NOT automated here (needs a machine whose user service manager the gateway can be
  installed as — a systemd user bus on Linux, launchd on macOS): the happy-path
  ``--apply --yes`` itself, ``--restore`` after a finished migration, the verify-failure
  rollback (gateway killed before verify), and a real ``thor update`` after a migration.
  This VM has no user D-Bus session, so the dry run is blocked here (exit 3) before any
  change, and faking a service manager would change the behaviour under test. Those
  steps are the manual checklist in
  ``website/docs/user-guide/features/web-dashboard.md`` ("Trying the move end to end").
  On a machine where the dry run exits 0, the ``--apply --yes`` refusal test below
  skips instead of performing a real migration in the suite.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.waiting import wait_until

ROOT = Path(__file__).resolve().parents[2]

_USERNAME = "probeuser"
_PASSWORD = "probe-pass-123"  # the one value that must never appear in any output


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan_exit_code(plan: dict) -> int:
    """The exit code the plan's own verdict implies (the JSON carries no ``exit_code`` field)."""
    if plan["blockers"]:
        return 3
    if plan["unsupported"]:
        return 6
    return 0


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port: int, path: str, auth: str | None = None) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {}
    if auth is not None:
        headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def _healthy(port: int) -> bool:
    try:
        return _get(port, "/api/health")[0] == 200
    except OSError:
        return False


def _child_env(home: Path) -> dict[str, str]:
    """The environment a real ``thor`` child runs in: this test's env, the temp home,
    the sign-in keys only the launcher carries (so the plan has keys to copy), and no
    lazy installs (a child must never download tools)."""
    env = {**os.environ, "THOR_HOME": str(home), "PYTHONPATH": str(ROOT),
           "THOR_DASHBOARD_BASIC_AUTH_USERNAME": _USERNAME,
           "THOR_DASHBOARD_BASIC_AUTH_PASSWORD": _PASSWORD}
    env.pop("THOR_RUNTIME_DIR", None)
    return env


def _run_thor(home: Path, *args: str, timeout: int = 180) -> subprocess.CompletedProcess:
    # check=False: the tests assert on the exit code themselves.
    return subprocess.run([sys.executable, "-m", "thor_cli.main", *args],
                          env=_child_env(home), capture_output=True, text=True,
                          timeout=timeout, check=False)


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)


class _OldBackend:
    """A real ``thor serve`` backend started by hand, with basic-auth sign-in active."""

    def __init__(self, home: Path):
        self.home = home
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None
        self._log = None
        self.config_before: str | None = None
        self.env_before: str | None = None

    def start(self) -> None:
        home = self.home
        home.mkdir(parents=True, exist_ok=True)
        (home / "config.yaml").write_text("model:\n  default: gemini-3.5-flash\n", encoding="utf-8")
        (home / ".env").write_text("", encoding="utf-8")  # sign-in lives in the launcher env only
        self.config_before = _digest(home / "config.yaml")
        self.env_before = _digest(home / ".env")
        log = open(home / "serve.log", "wb")
        self._log = log
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "thor_cli.main", "serve",
             "--host", "0.0.0.0", "--port", str(self.port)],
            env=_child_env(home), stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True)
        # Reap the child when it exits: an unreaped zombie still answers psutil with the
        # same start time, so the migration's same-process check would read it as alive.
        threading.Thread(target=self.proc.wait, daemon=True).start()
        wait_until(lambda: _healthy(self.port), timeout=90,
                   what="the real old backend to answer /api/health")

    def stop(self) -> None:
        if self.proc is not None:
            _stop(self.proc)
            self.proc = None
        if self._log is not None:
            self._log.close()
            self._log = None

    def address(self) -> str:
        return f"0.0.0.0:{self.port}"


@pytest.fixture
def backend(tmp_path):
    """A running old backend on a temp home; torn down (including any backend a rollback respawned)."""
    old = _OldBackend(tmp_path / "home")
    old.start()
    try:
        yield old
    finally:
        # A rollback respawns the backend under a new pid: stop that one too.
        manifest = old.home / "backend_migration.json"
        if manifest.exists():
            with contextlib.suppress(Exception):
                respawned = json.loads(manifest.read_text()).get("old_backend_respawned") or {}
                if (pid := respawned.get("pid")) and pid != (old.proc.pid if old.proc else None):
                    with contextlib.suppress(ProcessLookupError, PermissionError):
                        os.kill(pid, 15)
        old.stop()


@pytest.mark.platforms("linux")
def test_report_and_dry_run_see_the_real_manual_backend(backend, capsys, monkeypatch):
    """E2E (a)+(b): the report finds the hand-started backend and the dry run plans its
    address, names the sign-in keys to copy (never their values), and changes nothing."""
    home, port = backend.home, backend.port

    code, body = _get(port, "/api/health")
    assert code == 200
    assert json.loads(body)["auth_required"] is True
    code, body = _get(port, "/api/auth/providers")
    assert code == 200
    assert [p["name"] for p in json.loads(body)["providers"]] == ["basic"]

    report = _run_thor(home, "gateway", "migrate", "--backends")
    assert report.returncode == 0, report.stdout + report.stderr
    assert "manual" in report.stdout and f"PID {backend.proc.pid}" in report.stdout
    assert f"--host 0.0.0.0 --port {port}" in report.stdout  # the report shows the argv, not the address
    assert "--apply --dry-run" in report.stdout  # the NEXT_STEP footer

    dry = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--dry-run", "--json")
    assert dry.returncode in (0, 3, 6), dry.stdout + dry.stderr
    assert _PASSWORD not in dry.stdout and _PASSWORD not in dry.stderr
    payload = json.loads(dry.stdout)
    plan = payload["plan"]
    assert dry.returncode == _plan_exit_code(plan)
    assert plan["old_address"] == plan["new_address"] == backend.address()
    assert plan["copy_env_keys"] == ["THOR_DASHBOARD_BASIC_AUTH_PASSWORD",
                                     "THOR_DASHBOARD_BASIC_AUTH_USERNAME"]
    assert plan["auth_before"] == {"auth_required": True, "providers": ["basic"]}
    assert _digest(home / "config.yaml") == backend.config_before
    assert _digest(home / ".env") == backend.env_before
    assert not (home / "backend_migration.json").exists()  # a dry run leaves no record
    assert _healthy(port)  # the backend is still answering

    # A live turn blocks the move; --force-interrupt turns it into a consented takeover.
    # The marker is the backend's own durable format (tui_gateway.turn_marker): its writer
    # identity is the backend's pid + psutil create_time, which the liveness check compares.
    import psutil
    from tui_gateway import turn_marker
    marker_path = home / "desktop" / "interrupted_turns.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps({"probe-session": {
        "attempts": 0, "prompt": "a reply being written", "started_at": time.time(),
        "auto_continue": True, "writer_pid": backend.proc.pid,
        "writer_start_time": psutil.Process(backend.proc.pid).create_time()}}), encoding="utf-8")
    blocked = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--dry-run", "--json")
    blocked_plan = json.loads(blocked.stdout)["plan"]
    assert blocked_plan["running_turns"] == 1
    assert blocked.returncode == 3
    assert any("turn" in b for b in blocked_plan["blockers"])
    forced = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--dry-run", "--json",
                       "--force-interrupt")
    forced_plan = json.loads(forced.stdout)["plan"]
    assert forced_plan["running_turns"] == 1
    assert any("turn" in t.lower() or "repl" in t.lower() for t in forced_plan["takes_over"])
    turn_marker.clear_turn_marker(home, "probe-session")
    idle = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--dry-run", "--json")
    assert json.loads(idle.stdout)["plan"]["running_turns"] == 0

    # The update notice names the dry-run command for this home's real backend. The
    # in-process scan classifies a backend as this home's from the caller's THOR_HOME,
    # as a real `thor` invocation would carry it — so adopt the temp home first.
    monkeypatch.setenv("THOR_HOME", str(home))
    from thor_cli.update_backend_notice import old_backend_notice, print_old_backend_notice
    from thor_cli.update_cmd_fleet import _GatewayRestartOutcome
    from thor_cli.update_inventory import RuntimeRecord, UpdatePlan
    notice = old_backend_notice(home)
    assert notice is not None and "gateway migrate --backends --apply --dry-run" in notice
    print_old_backend_notice(
        UpdatePlan(profiles=["default"],
                   runtimes=[RuntimeRecord("serve", "default", backend.proc.pid, "manual-serve")]),
        _GatewayRestartOutcome(incomplete=False, phase_errors=[], pre_restart_gateway_pids=[],
                               restarted_services=[], failed_or_stale_units=[],
                               relaunched_profiles=[], externally_supervised_profiles=[],
                               killed_pids=set()))
    assert "gateway migrate --backends --apply --dry-run" in capsys.readouterr().out

    # Where the dry run is blocked (no user service manager on this machine), a real
    # --apply refuses before any change; where it is not blocked the full move is the
    # manual checklist, never a side effect of the suite.
    if _plan_exit_code(json.loads(idle.stdout)["plan"]) != 0:
        refused = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--yes")
        assert refused.returncode in (3, 6), refused.stdout + refused.stderr
        assert _digest(home / "config.yaml") == backend.config_before
        assert _digest(home / ".env") == backend.env_before
        assert not (home / "backend_migration.json").exists()
        assert _healthy(port)
    else:
        pytest.skip("this machine can drive the gateway service: the full move is manual-only")


@pytest.mark.platforms("linux")
def test_interrupted_run_is_rolled_back_by_the_next_apply(backend, monkeypatch):
    """E2E (e): a run interrupted after stopping the old backend is rolled back by the next
    ``--apply`` (exit 4): files byte-identical to before, the old backend answering again."""
    from thor_cli import gateway_migrate_backends_apply as apply_mod
    from thor_cli import gateway_migrate_backends_plan as plan_mod
    from thor_cli.gateway_migrate_backends_host import SystemHost

    home, port = backend.home, backend.port
    # The in-process plan classifies a backend as this home's from the caller's THOR_HOME,
    # as a real `thor` invocation would carry it — so adopt the temp home first.
    monkeypatch.setenv("THOR_HOME", str(home))
    host = SystemHost(home)
    plan = plan_mod.build_plan(host)
    assert plan.rec is not None and plan.rec["supervisor"] == "manual"
    assert plan.rec["pid"] == backend.proc.pid

    # The manifest a real run writes, before its first change.
    manifest = apply_mod.new_manifest(plan, host)
    apply_mod.write_manifest(home, manifest)
    # The writes a real run makes, through the real host seams, as far as stop_old_backend.
    writes = apply_mod.env_writes(plan)
    if writes:
        host.set_env(writes, expect=apply_mod._backup_digest(manifest, "env"))
    host.set_config(plan.config_writes(), expect=apply_mod._backup_digest(manifest, "config"))
    manifest["files_after_apply"] = {
        "config.yaml": _digest(home / "config.yaml"), ".env": _digest(home / ".env")}
    manifest["entered"] = ["preflight", "manifest", "webapp_bundle", "write_config", "stop_old_backend"]
    manifest["step"] = "stop_old_backend"
    manifest["steps"] = [{"name": n, "state": "running" if n == "stop_old_backend" else
                          ("done" if n in manifest["entered"] else "pending")}
                         for n in plan_mod.APPLY_STEPS]
    manifest["pid"] = 999999  # the run died: no such process
    manifest["pid_start_time"] = 12345
    apply_mod.write_manifest(home, manifest)
    assert (home / "config.yaml").read_bytes() != (home / "backend_migration" / "config.yaml.bak").read_bytes()

    # The interruption, as the dead run left it: the old backend stopped, the port free.
    host.old_stop(plan.rec)
    wait_until(lambda: not _healthy(port) and backend.proc.poll() is not None, timeout=60,
               what="the stopped old backend to go quiet")

    recovered = _run_thor(home, "gateway", "migrate", "--backends", "--apply", "--yes")
    assert recovered.returncode == 4, recovered.stdout + recovered.stderr
    assert "rolled back" in recovered.stdout.lower()

    done = apply_mod.read_manifest(home)
    assert done["state"] == "rolled_back"
    assert _digest(home / "config.yaml") == backend.config_before
    assert _digest(home / ".env") == backend.env_before
    wait_until(lambda: _healthy(port), timeout=90,
               what="the rolled-back old backend to answer /api/health again")
    code, body = _get(port, "/api/health")
    assert code == 200 and json.loads(body)["auth_required"] is True
    assert done["old_backend_respawned"]["pid"] != backend.proc.pid  # a fresh process serves it

    status = _run_thor(home, "gateway", "migrate", "--backends", "--status", "--json")
    assert status.returncode == 0
    assert json.loads(status.stdout)["state"] == "rolled_back"


@pytest.mark.platforms("linux")
def test_status_and_restore_without_any_migration(tmp_path):
    """E2E: with no manifest, ``--status`` reports ``none`` and ``--restore`` refuses (exit 3)."""
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  default: gemini-3.5-flash\n", encoding="utf-8")

    status = _run_thor(home, "gateway", "migrate", "--backends", "--status", "--json")
    assert status.returncode == 0
    assert json.loads(status.stdout)["state"] == "none"

    restore = _run_thor(home, "gateway", "migrate", "--backends", "--restore", "--yes")
    assert restore.returncode == 3
    assert "Nothing to restore" in restore.stdout
