"""``thor gateway migrate --backends --apply / --restore / --status`` (Fase 3).

Behaviour contracts only, driven by a fake host against a temporary home: the
manifest exists before the first change, files are written through a staged
copy that refuses edits made mid-run, a failed run rolls back, a finished
migration restores, a dead run is rolled back by the next invocation (never
continued), and the CLI usage rules exit 2.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.waiting import wait_until
from thor_cli import gateway_migrate_backends_apply as apply_mod
from thor_cli import gateway_migrate_backends_plan as plan_mod
from thor_cli.gateway_migrate_backends_host import FileChangedSinceBackup

_CONFIG_BEFORE = "model:\n  default: gemini-3.5-flash\n"
_ENV_BEFORE = "THOR_DASHBOARD_BASIC_AUTH_USERNAME=spike\n"


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rec(home: Path, *, was_active: bool = False) -> dict:
    return {"supervisor": "systemd", "unit": "thor-dashboard.service", "scope": "user",
            "unit_path": "/home/u/.config/systemd/user/thor-dashboard.service",
            "unit_file_state": "enabled", "was_active": was_active, "was_loaded": was_active,
            "pid": 4242, "start_time": 5242, "running": was_active,
            "thor_home": str(home), "this_home": True}


def _plan(home: Path, *, rec=None, carry=None, generate_secret=False) -> plan_mod.BackendPlan:
    return plan_mod.BackendPlan(
        home=str(home), rec=rec if rec is not None else _rec(home),
        old_host="127.0.0.1", old_port=9119, new_host="127.0.0.1", new_port=9119,
        gateway={"installed": False, "enabled": False, "active": False, "running_pid": None,
                 "kind": "systemd", "unit": "thor-gateway"},
        linger=None, auth_before=None, carry=carry or {}, generate_secret=generate_secret,
        keep_webapp=False)


class FakeHost:
    """The machine behind an apply: real files in a temp home, stubbed services."""

    def __init__(self, home: Path):
        self.home = Path(home)
        self.calls: list[str] = []
        self.gateway = {"installed": False, "enabled": False, "active": False,
                        "running_pid": None, "kind": "systemd", "unit": "thor-gateway"}
        self.gateway_status_value = {"gateway_state": "running", "auth_required": False,
                                     "auth_providers": []}
        self.fail_config_write = False

    def now(self) -> float:
        return 1700000000.0

    def sleep(self, seconds: float) -> None:
        pass

    def read_config(self) -> dict:
        return {}

    def process_env(self, pid):
        return {}

    def backends(self):
        return []

    def start_time(self, pid):
        return 1000 + pid if pid else None

    def same_process(self, pid, start):
        return False

    def running_turns(self, pid, start):
        return 0

    def gateway_state(self):
        return dict(self.gateway)

    def gateway_status(self, host, port):
        return None if self.gateway_status_value is None else dict(self.gateway_status_value)

    def webapp_page_problem(self, host, port):
        return None

    def gateway_pid(self):
        return 1234

    def pid_listens_on(self, pid, port):
        return True

    def port_in_use(self, host, port):
        return False

    def gateway_listens(self, port):
        return False

    def http_status(self, host, port):
        return {"health": "ok", "auth_required": False, "auth_providers": []}

    def old_unit_active(self, rec):
        return True

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
        return 4321

    def live_manual_backend(self, port):
        return None

    def install_gateway(self):
        self.gateway.update(installed=True, enabled=True)
        self.calls.append("install_gateway")

    _VERB_EFFECTS = {
        "start": ("active", True), "restart": ("active", True), "stop": ("active", False),
        "enable": ("enabled", True), "disable": ("enabled", False),
    }

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
        return None

    def _write_checked(self, path: Path, text: str, expect) -> bytes:
        current = _digest(path)
        if expect is not None and current != expect:
            raise FileChangedSinceBackup(f"{path.name} changed since the backup")
        path.write_text(text, encoding="utf-8")
        return path.read_bytes()

    def set_config(self, values: dict, *, expect):
        if self.fail_config_write:
            raise FileChangedSinceBackup("config.yaml changed since the backup")
        lines = ["webapp:"]
        for key, value in values.items():
            name = key.split(".", 1)[1]
            lines.append(f"  {name}: {value if not isinstance(value, bool) else str(value).lower()}")
        return self._write_checked(self.home / "config.yaml", "\n".join(lines) + "\n", expect)

    def set_env(self, values: dict, *, expect=False):
        path = self.home / ".env"
        lines = [f"{key}={value}" for key, value in values.items()]
        return self._write_checked(path, "\n".join(lines) + "\n", expect if expect is not False else None)

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
        return SimpleNamespace(enabled=True, host="127.0.0.1", port=9119,
                               public_url=None, reason=None)

    def gateway_kind(self):
        return "systemd"

    def stop_stray_gateway(self):
        return None


@pytest.fixture
def home(tmp_path):
    root = tmp_path / "home"
    root.mkdir()
    (root / "config.yaml").write_text(_CONFIG_BEFORE, encoding="utf-8")
    (root / ".env").write_text(_ENV_BEFORE, encoding="utf-8")
    return root


def test_manifest_is_written_before_the_first_change_with_readable_backups(home):
    """Apply — manifest & atomicity: the manifest (0600) and its backups
    (``backend_migration/`` 0700, files 0600) exist before anything changes,
    and the live files are still the originals."""
    host = FakeHost(home)
    manifest = apply_mod.new_manifest(_plan(home), host)
    apply_mod.write_manifest(home, manifest)  # the run persists it before its first change

    assert apply_mod.read_manifest(home) == manifest
    assert manifest["state"] == "running"
    assert stat.S_IMODE((home / "backend_migration.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((home / "backend_migration").stat().st_mode) == 0o700
    backups = manifest["backups"]
    assert Path(backups["config"]).read_bytes() == _CONFIG_BEFORE.encode()
    assert Path(backups["env"]).read_bytes() == _ENV_BEFORE.encode()
    assert stat.S_IMODE(Path(backups["config"]).stat().st_mode) == 0o600
    assert (home / "config.yaml").read_text() == _CONFIG_BEFORE
    assert (home / ".env").read_text() == _ENV_BEFORE


def test_apply_moves_the_backend_to_the_gateway_on_the_same_address(home):
    """Apply — happy path: exit 0, the manifest ends ``done``, the gateway is
    started and verified on the old address, the old backend is stopped."""
    host = FakeHost(home)

    assert apply_mod.apply(host, _plan(home)) == apply_mod.EXIT_OK

    manifest = apply_mod.read_manifest(home)
    assert manifest["state"] == "done"
    assert manifest["new_address"] == "127.0.0.1:9119"
    assert "old_stop" in host.calls and "gateway:start" in host.calls
    assert "webapp:" in (home / "config.yaml").read_text()
    assert host.gateway["active"] is True


def test_a_file_edited_since_its_backup_aborts_and_keeps_the_edit(home):
    """Apply — atomicity: when ``config.yaml`` changed since the backup, the
    apply refuses (exit 3), the edit is kept byte for byte, and the manifest
    records the rollback."""
    host = FakeHost(home)
    host.fail_config_write = True

    assert apply_mod.apply(host, _plan(home)) == apply_mod.EXIT_BLOCKED
    assert (home / "config.yaml").read_text() == _CONFIG_BEFORE
    assert apply_mod.read_manifest(home)["state"] == "rolled_back"


def test_restore_after_a_finished_migration_puts_the_files_back(home):
    """Rollback/restore: ``--restore`` after a finished migration returns 0,
    puts ``config.yaml``/``.env`` back byte for byte, and leaves state
    ``restored``."""
    host = FakeHost(home)
    assert apply_mod.apply(host, _plan(home)) == apply_mod.EXIT_OK

    assert apply_mod.restore(host, yes=True) == apply_mod.EXIT_OK

    manifest = apply_mod.read_manifest(home)
    assert manifest["state"] == "restored"
    assert (home / "config.yaml").read_text() == _CONFIG_BEFORE
    assert (home / ".env").read_text() == _ENV_BEFORE
    assert host.gateway["active"] is False


def test_restore_refuses_when_a_file_was_edited_since_the_migration(home):
    """Rollback/restore: a file edited after the migration blocks ``--restore``
    (exit 3) instead of overwriting the edit."""
    host = FakeHost(home)
    assert apply_mod.apply(host, _plan(home)) == apply_mod.EXIT_OK
    (home / "config.yaml").write_text(_CONFIG_BEFORE + "# my note\n", encoding="utf-8")

    assert apply_mod.restore(host, yes=True) == apply_mod.EXIT_BLOCKED
    assert "# my note" in (home / "config.yaml").read_text()
    assert apply_mod.read_manifest(home)["state"] == "done"


def _running_manifest(home: Path) -> dict:
    """A manifest left ``running`` by a dead run, with backups the rollback can read."""
    folder = home / "backend_migration"
    folder.mkdir(mode=0o700, exist_ok=True)
    config_bak = folder / "config.yaml.bak"
    env_bak = folder / "env.bak"
    apply_mod.write_private_file(config_bak, _CONFIG_BEFORE.encode())
    apply_mod.write_private_file(env_bak, _ENV_BEFORE.encode())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        "version": 1, "kind": "apply", "state": "running", "step": "write_config", "message": "",
        "steps": [{"name": n, "state": "done" if n in ("preflight", "manifest") else
                   ("running" if n == "write_config" else "pending")} for n in plan_mod.APPLY_STEPS],
        "entered": ["preflight", "manifest", "write_config"],
        "old_address": "127.0.0.1:9119", "new_address": "127.0.0.1:9119",
        "dial": {"host": "127.0.0.1", "old_host": "127.0.0.1", "verify_hosts": ["127.0.0.1"],
                 "old_port": 9119, "new_port": 9119},
        "started_at": 1700000000.0, "finished_at": None, "pid": 999999, "pid_start_time": 12345,
        "backups": {"config": str(config_bak), "env": str(env_bak), "launcher_env": None,
                    "config_mode": 0o644, "env_mode": 0o600},
        "old_backend": _rec(home), "old_backend_enabled": True,
        "gateway": {"installed": False, "enabled": False, "active": False},
        "linger": None, "webapp_before": None, "auth_before": None, "copied_env_keys": [],
        "keep_webapp_address": False,
        "files_after_apply": {"config.yaml": digest(config_bak), ".env": digest(env_bak)},
    }


def test_a_dead_run_is_rolled_back_by_the_next_invocation_not_continued(home):
    """Rollback/restore: a manifest left ``running`` by a dead pid is rolled
    back (exit 4, state ``rolled_back``) instead of resumed forward."""
    host = FakeHost(home)
    manifest = _running_manifest(home)
    apply_mod.write_manifest(home, manifest)
    assert apply_mod._in_progress(host, manifest) is False  # the pid is gone

    assert apply_mod.recover_interrupted(host, manifest) == apply_mod.EXIT_ROLLED_BACK
    assert apply_mod.read_manifest(home)["state"] == "rolled_back"
    assert (home / "config.yaml").read_text() == _CONFIG_BEFORE


def test_gateway_serving_requires_a_200_status_and_the_gateway_on_the_port(home):
    """Apply — verification: the gateway answers ``/api/status`` 200, serves
    the Webapp page and owns the listener, else a reason is returned."""
    host = FakeHost(home)
    manifest = {"dial": {"new_port": 9119, "verify_hosts": ["127.0.0.1"]},
                "auth_before": None, "keep_webapp_address": False}

    assert apply_mod.gateway_serving(host, manifest) is None

    host.gateway_status_value = None
    assert "no HTTP 200" in (apply_mod.gateway_serving(host, manifest) or "")


def test_unreadable_manifest_is_fail_closed(home):
    """Apply — manifest: a corrupt ``backend_migration.json`` is never treated
    as un-migrated and ``read_manifest`` returns None for it."""
    (home / "backend_migration.json").write_text("{not json", encoding="utf-8")

    assert apply_mod.read_manifest(home) is None
    assert apply_mod.unreadable_manifest(home) is not None
    assert "backend_migration.json" in apply_mod.unreadable_manifest(home)


def test_usage_error_rejects_each_bad_combination():
    """CLI — ``_usage_error``: the seven combination rules each exit 2."""

    def args(**overrides):
        base = {"apply": False, "restore": False, "status": False, "multiplex": False,
                "dry_run": False, "address": None, "keep_webapp_address": False,
                "force_interrupt": False, "expect": None, "detach": False}
        base.update(overrides)
        return SimpleNamespace(**base)

    assert apply_mod._usage_error(args()) is None
    assert apply_mod._usage_error(args(apply=True, restore=True)) is not None
    assert apply_mod._usage_error(args(apply=True, multiplex=True)) is not None
    assert apply_mod._usage_error(args(restore=True, dry_run=True)) is not None
    assert apply_mod._usage_error(args(address="127.0.0.1:9119")) is not None
    assert apply_mod._usage_error(args(detach=True)) is not None
    assert apply_mod._usage_error(args(address="not-an-address", apply=True)) is not None
    assert apply_mod._usage_error(args(apply=True, detach=True, dry_run=True)) is not None
    assert apply_mod._usage_error(args(apply=True, address="127.0.0.1:9119")) is None


def test_plan_token_is_stable_for_a_backend_and_changes_with_it(home):
    """CLI — ``--expect``: the same backend always yields the same token, a
    different unit a different one."""
    first = apply_mod.plan_token(_plan(home))
    assert first == apply_mod.plan_token(_plan(home))
    assert len(first) == 32
    other_rec = _rec(home)
    other_rec["unit"] = "thor-dashboard-other.service"
    assert apply_mod.plan_token(_plan(home, rec=other_rec)) != first


def test_status_payload_reports_none_done_and_an_interrupted_run(home):
    """Status: no manifest is ``none``, a finished one is ``done``, and a
    ``running`` manifest whose pid is gone says it was interrupted."""
    from thor_cli.gateway_migrate_backends_host import SystemHost
    host = SystemHost(home)

    assert apply_mod.status_payload(host)["state"] == "none"

    manifest = _running_manifest(home)
    apply_mod.write_manifest(home, manifest)
    payload = apply_mod.status_payload(host)
    assert payload["state"] == "running"
    assert "interrupted" in payload["message"]

    manifest["state"] = "done"
    apply_mod.write_manifest(home, manifest)
    assert apply_mod.status_payload(host)["state"] == "done"


def test_take_run_lock_refuses_when_another_process_holds_it(tmp_path):
    """Lock: a second run while another process holds the lock exits 3
    (``already_running``) and touches nothing."""
    home = tmp_path / "home"
    ready = tmp_path / "holder-ready"
    root = Path(__file__).resolve().parents[2]
    child = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, threading; sys.path.insert(0, sys.argv[1]); "
         "from thor_cli import gateway_migrate_backends_lock as lock; "
         "assert lock.acquire(__import__('pathlib').Path(sys.argv[2])); "
         "open(sys.argv[3], 'w').write('held'); threading.Event().wait(30)",
         str(root), str(home), str(ready)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THOR_HOME": str(home)})
    try:
        wait_until(lambda: ready.exists(), timeout=15, what="the holder child to take the lock")
        args = SimpleNamespace(dry_run=False, detach=False, detached_ack=None,
                               restore=False, json=False)
        assert apply_mod._take_run_lock(SimpleNamespace(home=home), args) == apply_mod.EXIT_BLOCKED
        assert not (home / "backend_migration.json").exists()
    finally:
        child.terminate()
        child.wait(timeout=10)


def _migrate_args(**overrides):
    base = {"backends": False, "json": False, "multiplex": False, "dry_run": False,
            "yes": False, "apply": False, "restore": False, "status": False,
            "address": None, "keep_webapp_address": False, "force_interrupt": False,
            "detach": False, "expect": None, "detached_run": False, "detached_ack": None}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_cmd_migrate_delegates_backend_flags_to_cmd_backends(monkeypatch):
    """CLI wiring: ``--backends`` with a backend flag reaches ``cmd_backends``,
    plain ``--backends`` still reaches the report."""
    from thor_cli import gateway_migrate
    from thor_cli import gateway_migrate_backends_apply as apply_module
    seen: list[str] = []
    monkeypatch.setattr(apply_module, "cmd_backends",
                        lambda args: seen.append("apply") or sys.exit(0))
    monkeypatch.setattr("thor_cli.gateway_migrate_backends.cmd_backends_report",
                        lambda args: seen.append("report"))

    with pytest.raises(SystemExit):
        gateway_migrate.cmd_migrate(_migrate_args(backends=True, status=True))
    assert seen == ["apply"]

    gateway_migrate.cmd_migrate(_migrate_args(backends=True))
    assert seen == ["apply", "report"]


def test_cmd_migrate_rejects_backend_flags_without_backends():
    """CLI wiring: a backend flag without ``--backends`` exits 2 with the
    documented message."""
    from thor_cli import gateway_migrate
    with pytest.raises(SystemExit) as excinfo:
        gateway_migrate.cmd_migrate(_migrate_args(apply=True))
    assert excinfo.value.code == 2


def test_backend_migration_store_is_registered_in_the_three_home_layouts(tmp_path, monkeypatch):
    """A8: the migration store is a credential store (home layout), excluded
    from profile clones, and hidden by the Files routes only under a Thor home
    (a project's own ``backend_migration/`` is not one)."""
    from thor_cli import home_data_layout, profiles
    from thor_cli.web_routers import files as files_router

    assert "backend_migration" in home_data_layout.CREDENTIAL_STORE_DIRS
    assert "backend_migration" in profiles._CLONE_ALL_HISTORY_EXCLUDE_ROOT
    assert "backend_migration.json" in profiles._CLONE_ALL_HISTORY_EXCLUDE_ROOT
    assert "backend_migration" in profiles.PROFILE_CREDENTIAL_PATHS

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("THOR_HOME", str(home))
    anchored = files_router._local_stores()[2]
    real_home = os.path.realpath(str(home))
    assert any(real_home in store for store in anchored)
    assert files_router._is_sensitive_path(Path("/tmp/project/backend_migration/notes.txt")) is False
    assert files_router._is_local_sensitive_path(
        home / "backend_migration" / "notes.txt", files_router._local_stores()) is True
