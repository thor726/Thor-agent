"""The docker build writes a GitHub Actions cache only where the export completes.

Regression (stable release rc.3-v0.23.6, run 46024985528, job 140594520239):
the slim/arm64 build finished in ~4 minutes, then stalled 41 minutes in
`exporting to GitHub Actions Cache` (cache-to type=gha,mode=max) until the
45-minute job timeout cancelled it. The amd64 cell with the identical
setting succeeded, and the desktop cells (which never write the cache)
succeeded -- so only the arm64 writer is dropped: the arm64 build itself
is fast without it, and a hung export must not fail the release lane.
"""
from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from tests.ci import _gha_expr as gha

ROOT = Path(__file__).resolve().parents[2]


def _cache_to() -> str:
    data = YAML(typ="base").load((ROOT / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8"))
    build = next(step for step in data["jobs"]["build"]["steps"]
                 if str(step.get("uses", "")).startswith("docker/build-push-action@"))
    return build["with"]["cache-to"]


def _rendered(event: str, variant: str, arch: str) -> str:
    return gha.render(_cache_to(), {"github": {"event_name": event},
                                    "matrix": {"variant": variant, "arch": arch}})


def test_arm64_build_writes_no_gha_cache():
    assert _rendered("push", "slim", "arm64") == ""
    assert _rendered("push", "desktop", "arm64") == ""


def test_amd64_slim_still_writes_its_gha_cache():
    assert _rendered("push", "slim", "amd64") == "type=gha,mode=max,scope=docker-amd64"
    assert _rendered("pull_request", "slim", "amd64") == ""
    assert _rendered("push", "desktop", "amd64") == ""
