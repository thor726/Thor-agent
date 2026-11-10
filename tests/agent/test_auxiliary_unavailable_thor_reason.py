"""The goal judge names a Thor auxiliary auth failure instead of an opaque judge error (#42177).

``_resolve_thor_runtime_api`` swallows the Thor resolver's ``AuthError`` so the ladder can fall
back; the failure must still reach the operator (one WARNING) and the goal-loop status line.
"""
import logging

import thor_yaml as yaml

import agent.auxiliary_unavailable as unavailable
from thor_cli.auth_constants import AuthError


def _reset(monkeypatch):
    monkeypatch.setattr(unavailable, "_last_thor_detail", None)
    monkeypatch.setattr(unavailable, "_warned_thor_details", set())


def test_goal_judge_reason_names_thor_auth_failure_and_still_fails_open(tmp_path, monkeypatch):
    """Real judge_goal → call_llm → ladder with goal_judge pinned to thor and no Thor login."""
    _reset(monkeypatch)
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({
        "model": {"provider": "thor", "default": "test-model"},
        "auxiliary": {"goal_judge": {"provider": "thor", "model": "test-model"}},
    }), encoding="utf-8")
    from thor_cli.goals import judge_goal

    verdict, reason, parse_failed, wait_directive, judge_errored = judge_goal(
        "ship the fix", "edited the file and ran the tests", timeout=5)

    assert (verdict, parse_failed, wait_directive, judge_errored) == ("continue", False, None, True)
    assert reason.startswith("goal_judge auxiliary client unavailable: Thor Portal runtime credentials unavailable:")
    assert "thor model" in reason, reason
    assert "judge error" not in reason


def test_thor_credential_failure_is_remembered_and_warned_once(caplog, monkeypatch):
    _reset(monkeypatch)
    exc = AuthError("Invalid refresh token", provider="thor", code="invalid_grant", relogin_required=True)
    with caplog.at_level(logging.WARNING, logger="agent.auxiliary_unavailable"):
        detail = unavailable.record_thor_credential_failure(exc)
        unavailable.record_thor_credential_failure(exc)

    assert detail.startswith("Thor Portal runtime credentials unavailable: ")
    assert "invalid_grant" in detail and "thor model" in detail
    assert unavailable.thor_credential_failure_detail() == detail
    assert sum(detail in rec.getMessage() for rec in caplog.records) == 1
    unavailable.clear_thor_credential_failure()
    assert unavailable.thor_credential_failure_detail() is None


def test_never_logged_in_is_debug_but_a_dead_credential_warns(caplog, monkeypatch, tmp_path):
    """The auto-route walk resolves Thor on every pass; users who never chose Thor must not be nagged."""
    _reset(monkeypatch)
    monkeypatch.setenv("THOR_HOME", str(tmp_path))
    not_logged_in = AuthError("Thor is not logged into Thor Portal.", provider="thor", relogin_required=True)
    dead = AuthError("Invalid refresh token", provider="thor", code="invalid_grant", relogin_required=True)
    with caplog.at_level(logging.DEBUG, logger="agent.auxiliary_unavailable"):
        quiet = unavailable.record_thor_credential_failure(not_logged_in)
        loud = unavailable.record_thor_credential_failure(dead)

    levels = {rec.levelno for rec in caplog.records if quiet in rec.getMessage()}
    assert levels == {logging.DEBUG}, caplog.records
    assert {rec.levelno for rec in caplog.records if loud in rec.getMessage()} == {logging.WARNING}
    assert "thor model" in quiet  # the goal judge still gets the remediation text
