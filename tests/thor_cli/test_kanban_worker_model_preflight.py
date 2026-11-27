"""A card whose profile names no model is refused before dispatch spawns a worker; a profile the
CLI and gateway serve through the provider's catalog default still spawns.

Fixture and refusal assertions adapted from upstream's test_kanban_worker_model_preflight.py."""

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def dispatch_profile(tmp_path, monkeypatch):
    from thor_cli import kanban_db as kb, kanban_db_dispatch as dispatch

    root = tmp_path / ".thor"
    profile = root / "profiles" / "worker"
    profile.mkdir(parents=True)
    (root / "config.yaml").write_text("model:\n  default: launch-model\n", encoding="utf-8")
    (profile / ".env").write_text("", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("THOR_HOME", str(root))
    monkeypatch.setenv("THOR_KANBAN_HOME", str(root))
    monkeypatch.delenv("THOR_KANBAN_DB", raising=False)
    monkeypatch.delenv("THOR_KANBAN_TASK", raising=False)
    monkeypatch.setattr(dispatch, "_memory_pressure_level", lambda: "normal")
    monkeypatch.setattr(dispatch, "_restart_safe_worker_argv", lambda task, command: command)
    spawned = []
    monkeypatch.setattr("subprocess.Popen", lambda command, **kw: spawned.append(command) or SimpleNamespace(pid=424242))
    kb.create_board("work")
    return profile, spawned


def _dispatch(profile, config_yaml, **task):
    from thor_cli import kanban_db as kb, kanban_db_dispatch as dispatch
    from thor_cli.kanban_db_connect import connect_closing

    (profile / "config.yaml").write_text(config_yaml, encoding="utf-8")
    with connect_closing(board="work") as conn:
        task_id = kb.create_task(conn, title="needs a model", assignee="worker", board="work", **task)
        result = dispatch.dispatch_once(conn, board="work")
        return task_id, result, kb.get_task(conn, task_id), kb.list_events(conn, task_id), kb.list_runs(conn, task_id)


def test_unresolved_model_refused_before_spawn_with_task_log(dispatch_profile):
    from thor_cli import kanban as cli

    profile, spawned = dispatch_profile
    task_id, result, task, events, runs = _dispatch(
        profile, "model:\n  provider: custom\n  base_url: https://llm.example.test/v1\n")
    assert not spawned and not result.spawned
    assert task.status == "ready" and task.worker_pid is None
    assert "No model configured for profile worker; pin one on this card with `thor kanban set-model`" in task.last_failure_error
    assert any(e.kind == "spawn_failed" and "thor -p worker model" in e.payload["error"] for e in events)
    assert len(runs) == 1 and runs[0].outcome == "spawn_failed"
    assert "thor -p worker model" in cli.run_slash(f"--board work log {task_id}")


@pytest.mark.parametrize("config_yaml, task", [
    ("model:\n  provider: openrouter\n", {}),
    ("model:\n  provider: custom\n  base_url: https://llm.example.test/v1\n", {"model_override": "task-model"}),
], ids=["catalog-default", "task-override"])
def test_resolvable_model_still_spawns(dispatch_profile, config_yaml, task):
    profile, spawned = dispatch_profile
    task_id, result, row, _, _ = _dispatch(profile, config_yaml, **task)
    assert len(spawned) == 1 and result.spawned[0][0] == task_id
    assert row.status == "running" and row.worker_pid == 424242


def _card(**kw):
    return SimpleNamespace(**{"id": "t_x", "assignee": "worker", "model_override": None, "provider_override": None, **kw})


_LAB_ENTRY = [{"name": "lab", "base_url": "https://lab.example.test/v1", "model": "entry-model"}]


@pytest.mark.parametrize("profile_model, expected", [
    ("profile-model", "profile-model"),
    ({"provider": "openrouter", "default": "profile-model"}, "profile-model"),
    ({"provider": "custom:lab"}, "entry-model"),
    ({"provider": "anthropic"}, "claude-opus-4-6"),
], ids=["string-profile", "profile-default", "held-named-entry", "catalog-default"])
def test_a_card_without_a_model_takes_the_profiles(profile_model, expected, monkeypatch):
    from thor_cli import models
    from thor_cli.kanban_worker_preflight import task_model

    monkeypatch.setattr(models, "get_default_model_for_provider", lambda provider: {"anthropic": "claude-opus-4-6"}.get(provider, ""))
    assert task_model(_card(), {"model": profile_model, "custom_providers": _LAB_ENTRY}) == (expected, False)


@pytest.mark.parametrize("config", [
    {"model": {"provider": "custom", "base_url": "http://127.0.0.1:9/v1"}},
    {"model": {"provider": "openrouter", "base_url": "http://127.0.0.1:8000/v1"}},
    {"model": {"provider": "lmstudio"}},
    {"model": {"provider": "llamacpp"}},
    {"model": {"provider": "custom", "base_url": "http://192.168.1.50:8000/v1"}},
    {"model": {"provider": "custom", "base_url": "https://box.tail1234.ts.net/v1"}},
    {"model": {"provider": "auto"}},
    {},
], ids=["custom-loopback", "builtin-loopback", "builtin-local-default", "managed-llamacpp",
        "lan-server", "tailnet-hostname", "auto", "unset"])
def test_deferred_routes_are_left_to_the_turn_without_a_network_call(config, tmp_path, monkeypatch):
    import socket

    from gateway.session_kanban import kanban_launch_policy
    from thor_cli import auth
    from thor_cli.kanban_worker_preflight import task_model

    opened = []

    def no_network(*args, **kwargs):
        opened.append(args)
        raise OSError("network blocked by test")

    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    real_resolve = auth.resolve_provider

    def resolve(requested=None, *args, **kwargs):
        if str(requested or "auto").strip().lower() == "auto":
            opened.append(("credential discovery", requested))
        return real_resolve(requested, *args, **kwargs)

    monkeypatch.setattr(auth, "resolve_provider", resolve)
    assert task_model(_card(), config) == ("", False)
    assert kanban_launch_policy(_card(reasoning_effort=None), str(tmp_path), config).model == ""
    assert opened == []


def test_preflight_never_imports_the_gateway_runner(tmp_path):
    import os
    import subprocess
    import sys

    root = tmp_path / ".thor"
    profile = root / "profiles" / "worker"
    profile.mkdir(parents=True)
    (profile / ".env").write_text("", encoding="utf-8")
    (profile / "config.yaml").write_text("model:\n  provider: custom\n  base_url: https://llm.example.test/v1\n", encoding="utf-8")
    probe = (
        "import os, sys\n"
        "from types import SimpleNamespace\n"
        "from thor_cli.kanban_worker_preflight import refuse_unresolved_model\n"
        "card = SimpleNamespace(id='t_fresh', assignee='worker', model_override=None, provider_override=None)\n"
        "try:\n"
        "    refuse_unresolved_model(card, '.', None)\n"
        "except RuntimeError as exc:\n"
        "    print('refused', exc)\n"
        "print('gateway.run' in sys.modules, os.environ.get('_THOR_GATEWAY'))\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "_THOR_GATEWAY"}
    env.update(HOME=str(tmp_path), THOR_HOME=str(root), THOR_KANBAN_HOME=str(root))
    out = subprocess.run([sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stderr
    lines = out.stdout.strip().splitlines()
    assert lines[0].startswith("refused No model configured for profile worker")
    assert f"THOR_HOME={profile.parent.parent}" in lines[0] and str(profile) not in lines[0]
    assert lines[-1] == "False None"
