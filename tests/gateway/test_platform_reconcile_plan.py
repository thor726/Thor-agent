"""Hot platform reconcile: the pure plan/print contract of ``gateway.run_platform_reconcile``.

The reconcile diff is generic: a build attempt records a :class:`BuildPrint` of what it read, and the
plan compares what the reloaded config wants against what was built and what is live. These tests pin
that contract (start / restart / stop / forget) and the control verb's answer for a home this gateway
does not serve — without starting a gateway.
"""
from types import SimpleNamespace

from gateway.config import Platform
from gateway.run_platform_reconcile import (
    BuildPrint,
    PlatformPlan,
    plan_platform_changes,
    reconcile_platforms_verb,
)


def _print(config: str, env: str | None = None) -> BuildPrint:
    return BuildPrint(config, env)


def test_plan_starts_wanted_restarts_stale_stops_gone_and_forgets_never_live():
    wanted = {
        Platform.TELEGRAM: _print("a"),
        Platform.SLACK: _print("b2"),
        Platform.FEISHU: _print("c"),
    }
    built = {
        Platform.SLACK: _print("b1"),
        Platform.FEISHU: _print("c"),
    }
    # telegram: wanted but never built -> start; slack: stale and live -> restart; feishu: identical
    # and live -> untouched. A built-but-unwanted platform that is live stops, one that never came
    # up is only forgotten. A platform built identically but never live is NOT started: the boot
    # attempt failed, and the boot verdict stands (upstream test_platform_hot_start.py).
    from gateway.config import Platform as P

    built[P.QQBOT] = _print("q")
    built[P.DISCORD] = _print("d")
    live = {Platform.SLACK, Platform.FEISHU, P.QQBOT}
    plan = plan_platform_changes(wanted, built, live)
    assert plan.start == (Platform.TELEGRAM,)
    assert plan.restart == (Platform.SLACK,)
    assert plan.stop == (P.QQBOT,)
    assert plan.forget == (P.DISCORD,)
    assert bool(plan) is True
    assert bool(PlatformPlan((), (), ())) is False
    unchanged = plan_platform_changes(
        {Platform.TELEGRAM: _print("a")}, {Platform.TELEGRAM: _print("a")}, set()
    )
    assert not unchanged and not unchanged.start


def test_build_print_differs_only_on_material_the_build_read():
    assert _print("a", "e1").differs(_print("a", "e1")) is False
    assert _print("a", "e1").differs(_print("b", "e1")) is True  # config changed
    assert _print("a", "e1").differs(_print("a", "e2")) is True  # env changed
    assert _print("a", None).differs(_print("a", "e2")) is False  # env not taken: no opinion
    assert _print("a", "e1").differs(_print("a", None)) is False


def test_reconcile_verb_refuses_a_home_this_gateway_does_not_serve(tmp_path):
    runner = SimpleNamespace(
        _primary_platform_home=lambda: tmp_path,
        _served_profile_homes={},
        reconcile_profile_platforms=None,
    )
    handler = reconcile_platforms_verb(runner, None)
    answer = handler({"home": str(tmp_path / "profiles" / "someone-else")})
    assert answer["applied"] is False
    assert "not served by this gateway" in answer["error"]
