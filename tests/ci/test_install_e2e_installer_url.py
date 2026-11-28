"""Install & update E2E desktop-installer legs skip when no installer URL is configured.

No Thor-Setup binary is published anywhere (the bootstrap installer is
built as a run artifact only, never published; every release has zero
assets), so the dmg-url / setup-exe-url defaults are empty and the
workflows must skip those legs instead of failing on the dead
thor-assets.thor-agent.local host (stable release rc.3-v0.23.6, run
46024985528: `curl: (6) Could not resolve host`).
"""
from __future__ import annotations

from pathlib import Path

import thor_yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    return thor_yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _inputs(data: dict) -> dict:
    # thor_yaml parses the `on:` key as boolean True (YAML 1.1).
    return (data.get("on") or data.get(True))["workflow_call"]["inputs"]


def test_macos_dmg_legs_skip_without_a_dmg_url():
    data = _load("install-e2e-macos-run.yml")
    assert _inputs(data)["dmg-url"]["default"] == ""
    job = data["jobs"]["gui-e2e"]
    assert "desktop-installer@latest" in str(job["if"])
    assert "inputs.dmg-url != ''" in str(job["if"])
    assert "thor-assets.thor-agent.local" not in (WORKFLOWS / "install-e2e-macos-run.yml").read_text(encoding="utf-8")


def test_windows_exe_legs_skip_without_a_setup_exe_url():
    data = _load("install-e2e-windows-run.yml")
    assert _inputs(data)["setup-exe-url"]["default"] == ""
    job = data["jobs"]["e2e"]
    assert "desktop-installer@latest" in str(job["if"])
    assert "(inputs.install-method != 'desktop-installer@latest' || inputs.setup-exe-url != '')" in str(job["if"])
    assert "(inputs.update-method != 'desktop-installer@latest' || inputs.setup-exe-url != '')" in str(job["if"])
    assert "thor-assets.thor-agent.local" not in (WORKFLOWS / "install-e2e-windows-run.yml").read_text(encoding="utf-8")
