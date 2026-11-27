"""``thor gateway migrate --backends --apply --dry-run``: the plan (changes nothing).

A fake host drives the real ``build_plan``: one old backend, the gateway's user service and
its ``GET /api/health`` read. Behaviour contracts only — the plan's address, credentials,
turns, unsupported supervisors and the OAuth sign-in refusal.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from thor_cli import gateway_migrate_backends_plan as plan_mod
from thor_cli.gateway_migrate_backends import BackendItem

_PASSWORD = "dummy-password-not-a-secret"
_SECRET = "dummy-secret-not-a-secret"


class FakeHost:
    """The machine behind ``build_plan``: one old backend plus the gateway's user service."""

    def __init__(self, home, *, supervisor="systemd", scope="user", running=True, argv=None,
                 env=None, cfg=None, turns=0, turns_known=True, health=None):
        self.home = Path(home)
        self._supervisor, self._scope, self._running = supervisor, scope, running
        self.argv = argv if argv is not None else [
            "/venv/bin/python", "-m", "thor_cli.main", "dashboard", "--no-open",
            "--host", "127.0.0.1", "--port", "9119"]
        self.env = env if env is not None else {
            "PATH": "/usr/bin",
            "THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike",
            "THOR_DASHBOARD_BASIC_AUTH_PASSWORD": _PASSWORD,
            "THOR_DASHBOARD_BASIC_AUTH_SECRET": _SECRET}
        self.cfg = cfg if cfg is not None else {}
        self.turns, self.turns_known = turns, turns_known
        self.health = health
        self.dotenv_map: dict = {}
        self.gateway = {"kind": "systemd", "unit": "thor-gateway", "installed": False,
                        "enabled": False, "active": False, "running_pid": None}

    # --- discovery
    def backends(self):
        if not self._running:
            return []
        return [BackendItem(supervisor=self._supervisor, running=True, pid=4242, argv=list(self.argv),
                            unit="thor-dashboard.service", scope=self._scope,
                            unit_path="/home/u/.config/systemd/user/thor-dashboard.service",
                            state="enabled", thor_home=str(self.home), this_home=True)]

    def os_family(self):
        return "linux"

    def username(self):
        return "u"

    def config_problem(self):
        return None

    def gateway_owner(self):
        return ("own", None)

    def effective_config(self):
        return dict(self.cfg)

    def dotenv(self):
        return dict(self.dotenv_map)

    def managed_env(self):
        return {}

    def dotenv_exists(self):
        return bool(self.dotenv_map) or (self.home / ".env").exists()

    def unit_props(self, unit, scope):
        return {"UnitFileState": "enabled", "ActiveState": "active" if self._running else "inactive",
                "ControlGroup": "/fake/thor-dashboard.service", "ExecStart": " ".join(self.argv)}

    def unit_environment(self, unit, scope):
        return dict(self.env), None

    def unit_launcher_env(self, unit, scope):
        return dict(self.env)

    def process_env(self, pid):
        return dict(self.env)

    def process_cwd(self, pid):
        return "/"

    def start_time(self, pid):
        return 1000 + pid

    def same_home(self, path):
        return str(path) == str(self.home)

    def default_home(self, env):
        return True

    def accepted_webapp_host(self, host):
        import ipaddress
        if host in ("localhost",):
            return host
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return None
        return host

    def webapp_settings(self):
        return SimpleNamespace(enabled=False, host="127.0.0.1", port=9120)

    def proposed_webapp_reason(self, *args):
        return None

    def gateway_state(self):
        return dict(self.gateway)

    def linger(self):
        return False

    def legacy_unit_records(self):
        return []

    def gateway_preflight(self):
        return None

    def gateway_environment(self):
        return {}, None

    def http_status(self, host, port):
        return self.health if self.health is not None else {
            "health": "ok", "auth_required": False, "auth_providers": []}

    def health_status(self, host, port):
        return self.http_status(host, port)

    def running_turns(self, pid, start_time):
        return self.turns if self.turns_known else None

    def unknown_turn_files(self, pid, start_time):
        return [] if self.turns_known else [str(self.home / "turn-marker")]

    def same_network_namespace(self, pid, container=False):
        return True

    def bundle_missing(self):
        return None


@pytest.fixture
def home(tmp_path, monkeypatch):
    root = tmp_path / "home"
    root.mkdir()
    monkeypatch.setenv("THOR_HOME", str(root))
    return root


def test_plan_target_keeps_old_bind_and_port(home):
    """Plan — address: the gateway takes the old backend's bind and port exactly (never wider)."""
    plan = plan_mod.build_plan(FakeHost(home))

    assert plan.exit_code() == plan_mod.EXIT_OK
    assert (plan.old_host, plan.old_port) == ("127.0.0.1", 9119)
    assert (plan.new_host, plan.new_port) == ("127.0.0.1", 9119)
    assert plan.to_dict()["new_address"] == "127.0.0.1:9119"
    assert plan.verify_hosts == ["127.0.0.1"]


def test_plan_unknown_address_is_a_blocker_not_a_guess(home):
    """Plan — address: ``--port 0`` (or an unreadable command line) blocks; no address is guessed."""
    argv = ["/venv/bin/python", "-m", "thor_cli.main", "dashboard", "--port", "0"]
    plan = plan_mod.build_plan(FakeHost(home, argv=argv))

    assert plan.exit_code() == plan_mod.EXIT_BLOCKED
    assert plan.new_host is None
    assert any("free port" in b for b in plan.blockers)
    assert plan.to_dict()["new_address"] is None


def test_plan_copies_signin_keys_by_name_only_and_never_prints_values(home):
    """Plan — credentials: launcher ``THOR_DASHBOARD_*`` keys are copied by name; values never
    appear in the plan text or JSON."""
    plan = plan_mod.build_plan(FakeHost(home))

    assert plan.exit_code() == plan_mod.EXIT_OK
    assert plan.carry == {"THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike",
                          "THOR_DASHBOARD_BASIC_AUTH_PASSWORD": _PASSWORD,
                          "THOR_DASHBOARD_BASIC_AUTH_SECRET": _SECRET}
    assert plan.generate_secret is False  # the launcher already has the signing secret
    rendered = "\n".join(plan_mod.format_plan(plan, dry_run=True)) + json.dumps(plan.to_dict())
    assert _PASSWORD not in rendered and _SECRET not in rendered
    assert "THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in rendered


def test_plan_template_env_value_that_would_resolve_differently_blocks(home):
    """Plan — credentials: a ``.env`` ``${VAR}`` template the gateway would resolve differently
    blocks the move instead of silently changing the sign-in."""
    (home / ".env").write_text("THOR_DASHBOARD_BASIC_AUTH_PASSWORD=${LAUNCH_VAR}\n", encoding="utf-8")
    host = FakeHost(home, env={"PATH": "/usr/bin", "LAUNCH_VAR": "launcher-value",
                               "THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike"})
    host.dotenv_map = {"THOR_DASHBOARD_BASIC_AUTH_PASSWORD": "${LAUNCH_VAR}"}

    plan = plan_mod.build_plan(host)

    assert plan.exit_code() == plan_mod.EXIT_BLOCKED
    assert any("THOR_DASHBOARD_BASIC_AUTH_PASSWORD" in b and "LAUNCH_VAR" in b for b in plan.blockers)


def test_plan_running_turns_block_and_force_interrupt_clears(home):
    """Plan — turns: running turns block; ``--force-interrupt`` turns the blocker into a
    ``takes_over`` entry instead."""
    blocked = plan_mod.build_plan(FakeHost(home, turns=2))
    assert blocked.exit_code() == plan_mod.EXIT_BLOCKED
    assert blocked.running_turns == 2
    assert any("2 turn(s) are running" in b for b in blocked.blockers)
    assert blocked.forceable and blocked.forceable[0] in blocked.blockers

    forced = plan_mod.build_plan(FakeHost(home, turns=2), force_interrupt=True)
    assert forced.exit_code() == plan_mod.EXIT_OK
    assert forced.blockers == [] and forced.forceable == []
    assert any("2 reply" in t or "2 turn" in t for t in forced.takes_over)


def test_plan_unreadable_turns_block_instead_of_reading_zero(home):
    """Plan — turns: turn activity that cannot be read is unknown (``running_turns`` null), never 0."""
    plan = plan_mod.build_plan(FakeHost(home, turns_known=False))

    assert plan.exit_code() == plan_mod.EXIT_BLOCKED
    assert plan.running_turns is None
    assert any("Cannot tell whether turns are running" in b for b in plan.blockers)


def test_plan_unsupported_supervisor_gets_manual_steps_and_exit_6(home):
    """Plan — supervisor tak didukung: Nix gets manual steps and exit 6; nothing is blocked."""
    plan = plan_mod.build_plan(FakeHost(home, supervisor="nix-systemd"))

    assert plan.exit_code() == plan_mod.EXIT_UNSUPPORTED
    assert plan.blockers == []
    assert len(plan.unsupported) == 1
    item, why, steps = plan.unsupported[0]
    assert item.supervisor == "nix-systemd"
    assert "Nix" in why
    assert any("Nix configuration" in s for s in steps)


def test_plan_oauth_signin_is_a_blocker_and_its_keys_are_never_carried(home):
    """OAuth carry-over is not supported: an old backend whose sign-in is the Nous Portal OAuth
    provider blocks the automatic move, and its OAuth keys are never copied to the gateway."""
    env = {"PATH": "/usr/bin", "THOR_DASHBOARD_OAUTH_CLIENT_ID": "agent:abc",
           "THOR_DASHBOARD_PORTAL_URL": "https://portal.example.invalid",
           "THOR_DASHBOARD_BASIC_AUTH_USERNAME": "spike"}
    health = {"health": "ok", "auth_required": True, "auth_providers": ["nous"]}
    plan = plan_mod.build_plan(FakeHost(home, env=env, health=health))

    assert plan.exit_code() == plan_mod.EXIT_BLOCKED
    assert "THOR_DASHBOARD_OAUTH_CLIENT_ID" not in plan.carry
    assert "THOR_DASHBOARD_PORTAL_URL" not in plan.carry
    assert any("OAuth" in b and "not carry" in b for b in plan.blockers)
    assert plan.auth_before == {"auth_required": True, "providers": ["nous"]}


def test_plan_oauth_signin_on_a_by_hand_backend_is_a_notice_not_a_blocker(home):
    """OAuth on a by-hand backend: the manual steps still print, with a notice that the OAuth
    keys must not be copied into .env."""
    env = {"PATH": "/usr/bin", "THOR_DASHBOARD_OAUTH_CLIENT_ID": "agent:abc"}
    plan = plan_mod.build_plan(FakeHost(home, supervisor="nix-systemd", env=env))

    assert plan.exit_code() == plan_mod.EXIT_UNSUPPORTED
    assert plan.blockers == []
    assert len(plan.unsupported) == 1 and plan.unsupported[0][2]  # steps still printed
    assert any("OAuth" in n and "do not copy THOR_DASHBOARD_OAUTH_CLIENT_ID" in n
               for n in plan.notices)
