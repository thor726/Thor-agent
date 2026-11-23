import asyncio
import logging
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.run import GatewayRunner
from gateway.session import AsyncSessionStore, SessionSource, SessionStore
from thor_cli import anon_auth
from thor_cli.commands import resolve_command


def _source(*, chat_type="dm", chat_id="chat-1", user_id="user-1", platform=Platform.TELEGRAM):
    return SessionSource(
        platform=platform, chat_id=chat_id, chat_type=chat_type, user_id=user_id)


def _runner(monkeypatch, *, extra=None):
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(platforms={
        Platform.TELEGRAM: PlatformConfig(enabled=True, token="token", extra=extra or {})})
    runner.adapters = {}
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    runner._session_model_overrides = {}
    runner.session_store = MagicMock()
    runner._async_session_store = MagicMock(set_model_override=AsyncMock())
    runner._async_session_store._store = runner.session_store
    runner._deliver_platform_notice = AsyncMock()
    runner._evict_cached_agent = MagicMock()

    async def inline(func):
        return func()

    runner._run_login_blocking = inline
    monkeypatch.setattr(anon_auth, "current_nous_state", lambda: None)
    return runner


def _event(**source_kwargs):
    return SimpleNamespace(source=_source(**source_kwargs))


async def _finish_tasks(runner):
    tasks = list(getattr(runner, "_background_tasks", ()))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)




@pytest.mark.asyncio
@pytest.mark.parametrize("chat_type", ["group", "channel", "thread", "webhook"])
async def test_non_direct_chats_are_refused_without_starting_anything(monkeypatch, chat_type):
    runner = _runner(monkeypatch)
    flow = MagicMock()
    monkeypatch.setattr(anon_auth, "run_sign_in", flow)

    result = await runner._handle_login_command(_event(chat_type=chat_type))

    assert result == anon_auth.LOGIN_DM_ONLY
    flow.assert_not_called()
    assert not hasattr(runner, "_background_tasks")


@pytest.mark.asyncio
async def test_a_dm_without_a_chat_id_is_refused(monkeypatch):
    runner = _runner(monkeypatch)
    assert await runner._handle_login_command(_event(chat_id="")) == anon_auth.LOGIN_DM_ONLY


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["ntfy", "raft", "a2a"])
async def test_broadcast_shaped_platforms_are_refused(monkeypatch, platform):
    runner = _runner(monkeypatch)
    flow = MagicMock()
    monkeypatch.setattr(anon_auth, "run_sign_in", flow)

    source = SimpleNamespace(
        platform=SimpleNamespace(value=platform), chat_id="chat-1", chat_type="dm", user_id="user-1")
    assert await runner._handle_login_command(SimpleNamespace(source=source)) == anon_auth.LOGIN_DM_ONLY
    flow.assert_not_called()


@pytest.mark.asyncio
async def test_already_signed_in_starts_no_task(monkeypatch):
    runner = _runner(monkeypatch)
    monkeypatch.setattr(anon_auth, "current_nous_state", lambda: {"auth_method": "oauth"})
    flow = MagicMock()
    monkeypatch.setattr(anon_auth, "run_sign_in", flow)

    assert await runner._handle_login_command(_event()) == anon_auth.UPGRADE_ALREADY_SIGNED_IN
    flow.assert_not_called()
    assert not hasattr(runner, "_background_tasks")


@pytest.mark.asyncio
async def test_a_non_admin_is_refused_when_gating_is_on(monkeypatch):
    runner = _runner(monkeypatch, extra={"allow_admin_from": ["operator"]})
    flow = MagicMock()
    monkeypatch.setattr(anon_auth, "run_sign_in", flow)

    assert await runner._handle_login_command(_event(user_id="other")) == anon_auth.LOGIN_NOT_ALLOWED
    flow.assert_not_called()


@pytest.mark.asyncio
async def test_a_completion_evicts_welcome_and_clears_its_override(monkeypatch):
    runner = _runner(monkeypatch)
    agent = SimpleNamespace(provider="nous", model=anon_auth.GUEST_MODEL)
    runner._agent_cache = {"k1": (agent, "signature")}
    runner._session_model_overrides["k1"] = {"model": anon_auth.GUEST_MODEL}

    await runner._render_login_state(
        SimpleNamespace(source=_source(), attempt_id="attempt"),
        anon_auth.Completed(email="person@example.test", model="model-1", model_changed=True),
    )

    runner._evict_cached_agent.assert_called_once_with("k1")
    assert "k1" not in runner._session_model_overrides
    runner.async_session_store.set_model_override.assert_awaited_once_with("k1", None)


def _durable_sweep_runner(monkeypatch, tmp_path):
    import thor_state

    def no_sqlite(**_kwargs):
        raise RuntimeError("Exercise sessions.json persistence")

    monkeypatch.setattr(thor_state, "SessionDB", no_sqlite)
    runner = _runner(monkeypatch)
    store = SessionStore(sessions_dir=tmp_path, config=runner.config)
    key = store.get_or_create_session(_source()).session_key
    override = {"model": anon_auth.GUEST_MODEL}
    store.set_model_override(key, override)
    runner.session_store = store
    runner._async_session_store = AsyncSessionStore(store)
    runner._session_model_overrides[key] = dict(override)
    runner._agent_cache[key] = (
        SimpleNamespace(provider="nous", model=anon_auth.GUEST_MODEL), "signature")
    return runner, store, key, override


@pytest.mark.asyncio
async def test_durable_clear_fails_once_then_succeeds_before_eviction(monkeypatch, tmp_path):
    runner, store, key, override = _durable_sweep_runner(monkeypatch, tmp_path)
    save = store._save_sessions_json
    writes = []

    def fail_once(data):
        writes.append(data)
        assert runner._session_model_overrides[key] == override
        runner._evict_cached_agent.assert_not_called()
        if len(writes) == 1:
            raise OSError("disk temporarily unavailable")
        save(data)

    monkeypatch.setattr(store, "_save_sessions_json", fail_once)
    attempt = SimpleNamespace(source=_source(), attempt_id="attempt")
    state = anon_auth.Completed(model="model-1", model_changed=True)

    await runner._render_login_state(attempt, state)

    assert len(writes) == 2
    assert key not in runner._session_model_overrides
    runner._evict_cached_agent.assert_called_once_with(key)
    reloaded = SessionStore(sessions_dir=tmp_path, config=runner.config)
    assert reloaded.get_model_override(key) is None
    runner._deliver_platform_notice.assert_awaited_once_with(attempt.source, state.copy)


@pytest.mark.asyncio
async def test_durable_clear_fails_twice_keeps_override_and_warns(monkeypatch, tmp_path, caplog):
    runner, store, key, override = _durable_sweep_runner(monkeypatch, tmp_path)
    # Multiple failed sessions still produce exactly one extra completion line.
    second_key = store.get_or_create_session(_source(chat_id="chat-2")).session_key
    store.set_model_override(second_key, override)
    runner._session_model_overrides[second_key] = dict(override)
    runner._agent_cache[second_key] = runner._agent_cache[key]
    writes = []

    def fail_always(data):
        writes.append(data)
        raise OSError("disk unavailable")

    monkeypatch.setattr(store, "_save_sessions_json", fail_always)
    attempt = SimpleNamespace(source=_source(), attempt_id="attempt")
    state = anon_auth.Completed(model="model-1", model_changed=True)
    with caplog.at_level(logging.WARNING, logger="gateway.run"):
        await runner._render_login_state(attempt, state)

    assert len(writes) == 4
    reloaded = SessionStore(sessions_dir=tmp_path, config=runner.config)
    rebuilt = _runner(monkeypatch)
    rebuilt.session_store = reloaded
    for session_key in (key, second_key):
        assert runner._session_model_overrides[session_key] == override
        assert reloaded.get_model_override(session_key) == override
        rebuilt._rehydrate_session_model_override(session_key)
        assert rebuilt._session_model_overrides[session_key]["model"] == override["model"]
        assert any(
            record.levelno == logging.WARNING and session_key in record.getMessage()
            and "failed to clear free-tier override" in record.getMessage()
            for record in caplog.records)
    runner._evict_cached_agent.assert_not_called()
    runner._deliver_platform_notice.assert_awaited_once_with(
        attempt.source,
        state.copy + "\nSome chats are still on the free tier; use /model in those chats to switch.")


@pytest.mark.asyncio
async def test_the_sweep_leaves_sessions_on_other_models_alone(monkeypatch):
    runner = _runner(monkeypatch)
    runner._agent_cache = {
        "k1": (SimpleNamespace(provider="nous", model=anon_auth.GUEST_MODEL), "signature"),
        "k2": (SimpleNamespace(provider="openrouter", model="openrouter/x"), "signature"),
    }
    runner._session_model_overrides["k2"] = {"model": "openrouter/x"}

    await runner._render_login_state(
        SimpleNamespace(source=_source(), attempt_id="attempt"),
        anon_auth.Completed(email="person@example.test", model="model-1", model_changed=True),
    )

    assert runner._evict_cached_agent.call_args_list == [call("k1")]
    assert runner._session_model_overrides["k2"] == {"model": "openrouter/x"}
    runner.async_session_store.set_model_override.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_sweep_is_skipped_when_the_model_did_not_change(monkeypatch):
    runner = _runner(monkeypatch)
    runner._agent_cache = {
        "k1": (SimpleNamespace(provider="nous", model=anon_auth.GUEST_MODEL), "signature")}

    await runner._render_login_state(
        SimpleNamespace(source=_source(), attempt_id="attempt"),
        anon_auth.Completed(email="person@example.test", model="model-1", model_changed=False),
    )

    runner._evict_cached_agent.assert_not_called()
    runner.async_session_store.set_model_override.assert_not_awaited()
    assert "person@example.test" in runner._deliver_platform_notice.await_args_list[-1].args[1]


@pytest.mark.asyncio
async def test_a_completion_with_no_default_names_the_slash_command(monkeypatch):
    runner = _runner(monkeypatch)

    await runner._render_login_state(
        SimpleNamespace(source=_source(), attempt_id="attempt"),
        anon_auth.Completed(email="person@example.test", model="", model_changed=True),
    )

    assert "/model" in runner._deliver_platform_notice.await_args_list[-1].args[1]


@pytest.mark.asyncio
async def test_a_failing_sweep_still_pushes_the_completion(monkeypatch, caplog):
    runner = _runner(monkeypatch)
    runner._evict_cached_agent = MagicMock(side_effect=RuntimeError("boom"))
    runner._agent_cache = {
        "k1": (SimpleNamespace(provider="nous", model=anon_auth.GUEST_MODEL), "signature")}
    attempt = SimpleNamespace(source=_source(), attempt_id="attempt")
    state = anon_auth.Completed(email="person@example.test", model="model-1", model_changed=True)

    await runner._render_login_state(attempt, state)

    runner._deliver_platform_notice.assert_awaited_once_with(attempt.source, state.copy)
    assert "failed to evict free-tier session" in caplog.text


@pytest.mark.asyncio
async def test_shutdown_cancellation_marks_the_attempt_cancelled(monkeypatch):
    runner = _runner(monkeypatch)
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked(_func):
        started.set()
        await release.wait()

    runner._run_login_blocking = blocked
    attempt = SimpleNamespace(
        attempt_id="attempt", key=("telegram", "chat-1", "user-1"),
        source=_source(), cancelled=False)
    task = asyncio.create_task(runner._run_login(attempt))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert attempt.cancelled is True


@pytest.mark.asyncio
async def test_the_drain_never_touches_the_shared_executor(monkeypatch):
    runner = _runner(monkeypatch)
    runner._get_executor = MagicMock(side_effect=AssertionError("shared executor used"))
    monkeypatch.setattr(anon_auth, "run_sign_in", lambda **_kwargs: iter([anon_auth.TimedOut()]))
    del runner.__dict__["_run_login_blocking"]

    await runner._run_login(SimpleNamespace(
        attempt_id="attempt", key=("telegram", "chat-1", "user-1"),
        source=_source(), cancelled=False))

    runner._get_executor.assert_not_called()
    runner._login_exec.shutdown(wait=True)


@pytest.mark.asyncio
async def test_login_dispatches_mid_turn():
    runner = object.__new__(GatewayRunner)
    runner._handle_login_command = AsyncMock(return_value="started")
    command = resolve_command("login")
    event = _event()

    assert await runner._dispatch_busy_slash_command(event, command, "", event.source) == "started"
    runner._handle_login_command.assert_awaited_once_with(event)



@pytest.mark.asyncio
async def test_a_dm_returns_thorhub_guidance_instead_of_starting_oauth(monkeypatch):
    """Debrand Fase 2: /login tidak lagi memulai OAuth Nous — balasannya
    mengarahkan ke ThorHub (toko token) + cara pasang key."""
    runner = _runner(monkeypatch)
    flow = MagicMock()
    monkeypatch.setattr(anon_auth, "run_sign_in", flow)

    result = await runner._handle_login_command(_event())

    assert "llm.thormarket.site/beli" in result
    assert "llm.thormarket.site/v1" in result
    assert "/skill saldo" in result
    assert "/skill beli" in result
    flow.assert_not_called()
    assert not hasattr(runner, "_background_tasks")
    assert "login" not in getattr(runner, "_login_attempts", {})


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_type", ["dm", "private"])
async def test_dm_and_private_chats_get_the_same_guidance(monkeypatch, chat_type):
    runner = _runner(monkeypatch)
    result = await runner._handle_login_command(_event(chat_type=chat_type))
    assert "ThorHub" in result
    assert "llm.thormarket.site" in result
