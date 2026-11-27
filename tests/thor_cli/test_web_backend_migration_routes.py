"""The dashboard's backend-migration routes (``/api/gateway/migrate/backends/*``) through the real app.

The engine's host is a fake for the service manager, the process table and the network (as in the
engine's own tests); the plan, the manifest reader and ``status_payload`` are the real engine code, the
auth gate is the app's real middleware, and only the action spawner is recorded instead of run (it
would start ``systemd-run --user`` on the test machine).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from thor_cli import web_server
from thor_cli import gateway_migrate_backends_apply as engine
from thor_cli import gateway_migrate_backends_plan
from thor_cli.gateway_migrate_backends import BackendItem
from thor_cli.gateway_migrate_backends_host import SystemHost
from thor_cli.web_routers import backend_migration as routes

_PASSWORD = "pw-route-never-returned-5e2a"
_PID = 4242
_ROUTES = [("GET", "/api/gateway/migrate/backends/plan"), ("POST", "/api/gateway/migrate/backends/apply"),
           ("POST", "/api/gateway/migrate/backends/restore"), ("GET", "/api/gateway/migrate/backends/status")]


class FakeHost(SystemHost):
    """One old dashboard as a systemd user unit on 0.0.0.0:9119 whose ExecStart carries the password."""

    def __init__(self, home, *, running_turns=0):
        super().__init__(home)
        self.turns = running_turns

    def backends(self):
        return [BackendItem(supervisor="systemd", running=True, pid=_PID,
                            argv=["/usr/bin/env", f"THOR_DASHBOARD_BASIC_AUTH_PASSWORD={_PASSWORD}",
                                  "/venv/bin/thor", "dashboard", "--no-open", "--host", "0.0.0.0", "--port", "9119"],
                            unit="thor-dashboard.service", scope="user",
                            unit_path="/home/u/.config/systemd/user/thor-dashboard.service", state="enabled",
                            thor_home=str(self.home), this_home=True)]

    def is_root(self):
        return False

    def os_family(self):
        return "linux"

    def unit_props(self, unit, scope):
        return {"UnitFileState": "enabled", "ActiveState": "active", "ControlGroup": f"/fake/{unit}"}

    def process_env(self, pid):
        return {"THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike", "THOR_DASHBOARD_BASIC_AUTH_PASSWORD": _PASSWORD}

    def process_cwd(self, pid):
        return f"/home/u/{_PASSWORD}"

    def start_time(self, pid):
        return 1000 + pid

    def same_process(self, pid, start_time):
        return False

    def own_unit(self):  # never the test runner's own cgroup
        return None

    def running_turns(self, pid, start_time):
        return self.turns

    def bundle_missing(self):
        return None

    def gateway_kind(self):
        return "systemd"

    def gateway_state(self):
        return {"kind": "systemd", "unit": "thor-gateway", "installed": False, "enabled": False, "active": False,
                "running_pid": None}

    def gateway_preflight(self):
        return None

    def legacy_unit_records(self):  # no pre-rename thor.service
        return []

    def linger(self):
        return False

    def gateway_owner(self):  # every test profile has its own gateway service
        return "own", None

    def http_status(self, host, port):  # shaped like SystemHost's: GET /api/health (+ providers)
        return {"ok": True, "auth_required": True, "auth_providers": ["basic"]}

    def same_network_namespace(self, pid, *, container):  # the fake pid is never looked up in /proc
        return True

    def health_status(self, host, port):  # the by-hand plan's health-only read, from the same fake answer
        return self.http_status(host, port)


@pytest.fixture(autouse=True)
def _standard_root(monkeypatch):
    """The homes here stand for the user's standard Thor root, so commands read ``thor -p NAME`` (as in
    the engine's tests); the root pin for a temp root is tested on its own below."""
    monkeypatch.setattr(gateway_migrate_backends_plan, "_is_standard_root", lambda root: True)


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "thor-home"
    (h / "logs").mkdir(parents=True)
    monkeypatch.setenv("THOR_HOME", str(h))
    (h / "config.yaml").write_text("model:\n  default: fake-model\n", encoding="utf-8")
    (h / ".env").write_text("OPENAI_API_KEY=***\n", encoding="utf-8")
    os.chmod(h / ".env", 0o600)
    return h


@pytest.fixture
def spawned(home, tmp_path, monkeypatch):
    """Records each launcher instead of starting it; the launcher answers as the real one does when its
    background run holds the lock: exit 0 and its ``--json`` line (``confirmed: true``) in its own output."""
    calls: list[dict] = []
    monkeypatch.setattr("thor_cli.web_server_gateway._ACTION_LOG_DIR", tmp_path / "action-logs")

    def record(subcommand, name, *, env_overrides=None, output=None):
        calls.append({"argv": list(subcommand), "name": name, "env": dict(env_overrides or {})})
        launcher_says(Path((env_overrides or {})["THOR_HOME"]), output, confirmed=True)
        return SimpleNamespace(pid=777, poll=lambda: 0, wait=lambda timeout=None: 0)

    monkeypatch.setattr("thor_cli.web_server_gateway._spawn_thor_action", record)
    return calls


def launcher_says(home: Path, output, *, confirmed: bool) -> None:
    line = {"detached": True, "mode": "apply", "unit": "x.service", "confirmed": confirmed,
            "log": str(home / "logs" / "backend-migration.log")}
    output.write(f"=== gateway-migrate-backends started ===\n{json.dumps(line)}\n".encode())


def _client(home, monkeypatch, **host_kw):
    monkeypatch.setattr(routes, "_host", lambda target_home: FakeHost(target_home, **host_kw))
    client = TestClient(web_server.app)
    client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
    return client


def test_routes_need_the_dashboard_session_token(home, spawned, monkeypatch):
    """Same gate as every action route: no session token, no answer; with it, the plan answers the plan,
    the read-only report and the last run."""
    authed = _client(home, monkeypatch)
    anon = TestClient(web_server.app)
    for method, path in _ROUTES:
        assert anon.request(method, path).status_code == 401, path
    assert spawned == []

    plan = authed.get("/api/gateway/migrate/backends/plan")
    assert plan.status_code == 200, plan.text
    body = plan.json()
    assert body["plan"]["old_address"] == "0.0.0.0:9119"
    assert body["plan"]["found"] is True
    assert [item["supervisor"] for item in body["report"]] == ["systemd"]
    assert body["run"]["state"] == "none"
    assert spawned == []


def test_apply_with_a_stale_expect_token_is_409_plan_changed_and_starts_nothing(home, spawned, monkeypatch):
    """A confirmation never moves a backend the user was not shown: a mismatched ``expect`` is refused
    with the fresh plan and starts nothing; the shown token starts the detached run."""
    client = _client(home, monkeypatch)
    shown = client.get("/api/gateway/migrate/backends/plan").json()["plan"]
    assert shown["expect_token"]

    changed = client.post("/api/gateway/migrate/backends/apply",
                          json={"address": shown["old_address"], "expect": "stale-token"})
    assert changed.status_code == 409 and changed.json()["error"] == "plan_changed", changed.text
    assert changed.json()["plan"]["expect_token"] == shown["expect_token"]
    assert spawned == []

    started = client.post("/api/gateway/migrate/backends/apply",
                          json={"address": shown["old_address"], "expect": shown["expect_token"]})
    assert started.status_code == 200, started.text
    assert started.json()["ok"] is True and started.json()["confirmed"] is True
    assert spawned[-1]["argv"] == ["-p", "default", "gateway", "migrate", "--backends", "--apply", "--yes", "--detach",
                                   "--json", "--address", "0.0.0.0:9119", "--expect", shown["expect_token"]]
    assert spawned[-1]["name"] == "gateway-migrate-backends"
    assert spawned[-1]["env"] == {"THOR_HOME": str(home)}


def test_no_secret_value_or_backend_argv_in_any_response(home, spawned, monkeypatch):
    """The password lives only in the old unit's ExecStart, cwd and environment, then in ``.env``; no
    response carries its value, the old backend's argv or its cwd (only key names)."""
    client = _client(home, monkeypatch)
    # Before the move the password is only in the old unit's ExecStart, cwd and environment.
    bodies = [client.get("/api/gateway/migrate/backends/plan"), client.post("/api/gateway/migrate/backends/apply")]
    # After it the value lives in .env; a log line that ever echoed it must not reach the page.
    (home / ".env").write_text(f"THOR_DASHBOARD_BASIC_AUTH_PASSWORD={_PASSWORD}\n", encoding="utf-8")
    (home / "logs" / "backend-migration.log").write_text(f"oops {_PASSWORD}\n✓ Migrated\n", encoding="utf-8")
    bodies.append(client.get("/api/gateway/migrate/backends/status"))

    assert [b.status_code for b in bodies] == [200, 200, 200]
    plan = bodies[0].json()["plan"]
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in plan["copy_env_keys"]  # the name is shown...
    for b in bodies:
        assert _PASSWORD not in b.text  # ...the value never is (not via argv, cwd, env or the log)
        assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD=" not in b.text
    assert "/venv/bin/thor" not in bodies[0].text  # the old backend's argv never leaves the server
    assert f"/home/u/{_PASSWORD}" not in bodies[0].text
