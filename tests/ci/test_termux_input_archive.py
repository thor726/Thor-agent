"""CI runs archival before the exact tool and payload consumers."""
import json
from pathlib import Path

import pytest

from ruamel.yaml import YAML

from tests.ci.desktop_release_roles import DOWNLOADABLE_DISPATCHES, gate, needs_of
from tests.ci.workflow_steps import is_checkout

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ENV = {"GH_TOKEN", "THOR_ARCHIVE_RELEASE"}


def load(name):
    return YAML(typ="base").load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_archive_reader_accepts_bom_without_changing_pin_authority(tmp_path):
    from scripts.ci.archive_inputs import pinned_inputs

    (tmp_path / "pm").mkdir()
    (tmp_path / "pm/lock.json").write_bytes(b'\xef\xbb\xbf{"schema":1,"packages":{}}')
    table = tmp_path / "pm/termux_runtime_libs.json"
    row = {"url": "https://example.invalid/café.deb", "sha256": "a" * 64}
    table.write_bytes(b"\xef\xbb\xbf" + json.dumps({"libs": {"lib": row}}, ensure_ascii=False).encode("utf-8"))
    before = table.read_bytes()
    (pin,) = pinned_inputs(tmp_path, target="linux-arm64-bionic")
    assert (pin.name, pin.url, pin.sha256) == ("lib", row["url"], row["sha256"])
    assert table.read_bytes() == before
    row["sha256"] = " " + row["sha256"]
    table.write_bytes(b"\xef\xbb\xbf" + json.dumps({"libs": {"lib": row}}).encode("utf-8"))
    with pytest.raises(ValueError):
        pinned_inputs(tmp_path, target="linux-arm64-bionic")


def test_archive_gate_uses_bootstrap_python_and_trusted_exact_revision():
    workflow = load("archive-inputs.yml")
    assert not {"pull_request", "pull_request_target"} & workflow["on"].keys()
    assert "workflow_dispatch" in workflow["on"] and "push" in workflow["on"]
    job = workflow["jobs"]["archive-inputs"]
    assert job["environment"] == "release-signing"
    # The archive is the ci-archive GitHub release, written with the job token.
    assert ARCHIVE_ENV <= job["env"].keys()
    assert job["env"]["THOR_ARCHIVE_RELEASE"] == "ci-archive"
    assert not any(s.get("uses") == "./.github/actions/setup-pm" for s in job["steps"])
    (archive,) = [s for s in job["steps"] if s.get("run") == "python3 -m scripts.ci.archive_inputs"]
    # Forks cannot write the archive release; they skip with a notice instead.
    assert "fork" in archive["if"]
    assert any("fork" in str(s.get("if", "")) and "notice" in str(s.get("run", ""))
               for s in job["steps"])
    checkout = job["steps"][0]
    assert checkout["with"]["ref"] == "${{ inputs.sha || github.sha }}"
    release = load("desktop-bundled-release.yml")
    assert ARCHIVE_ENV <= release["env"].keys()
    release_jobs = release["jobs"]
    # The archive lives as a validate step with the job's own gate shape —
    # a skipped archive (disposable/termux runs) must not skip the builds.
    validate = release_jobs["validate"]
    (archive,) = [s for s in validate["steps"] if s.get("run") == "python3 -m scripts.ci.archive_inputs"]
    for dispatch, inputs in DOWNLOADABLE_DISPATCHES.items():
        assert gate(archive["if"], inputs, {}, job_if=False), dispatch
    for skipped in ({"disposable_run": "98765"}, {"disposable_channel": "native-preview"},
                    {"release-phase": "publish"}, {"release-phase": "promote"}):
        assert not gate(archive["if"], {**DOWNLOADABLE_DISPATCHES["tag"], **skipped}, {}, job_if=False), skipped
    assert validate["environment"] == "release-signing"
    assert is_checkout(validate["steps"][0])
    assert not [name for name, job in release_jobs.items() if "archive-inputs" in needs_of(job)]

    action = YAML(typ="base").load((ROOT / ".github/actions/setup-pm/action.yml").read_text(encoding="utf-8"))
    assert action["inputs"]["archive-inputs"]["default"] == "false"
    steps = action["runs"]["steps"]
    archive_index, archive = next((i, s) for i, s in enumerate(steps) if "setup_toolchain.py\" archive-inputs" in s.get("run", ""))
    assert gate(archive["if"], {"archive-inputs": "true"}, {}, job_if=False)
    assert not gate(archive["if"], {"archive-inputs": "false"}, {}, job_if=False)
    assert archive_index < next(i for i, s in enumerate(steps) if s.get("id") == "install")


def test_scheduled_and_main_consumers_skip_without_archive_access():
    """Only explicit release runs may fail on a missing archive; main and the nightly stay green."""
    prune = load("canary-release.yml")["jobs"]["prune"]
    # Tag pruning is release.py's; no step may call the retired object-store module.
    assert not [s for s in prune["steps"] if "scripts.releases.r2" in s.get("run", "")]
    assert any("release.py" in s.get("run", "") and "--prune-canaries" in s.get("run", "")
               for s in prune["steps"])

    termux = load("termux-verify.yml")
    assert termux["on"]["push"]["branches"] == ["main"] and "pull_request" in termux["on"]
    native = termux["jobs"]["native-runtime"]
    probe = termux["jobs"][native["needs"]]
    assert probe["environment"] == "release-signing"
    for configured, release, runs in (("true", False, True), ("false", True, True), ("false", False, False),
                                      ("", False, False)):
        needs = {native["needs"]: {"result": "success", "outputs": {"configured": configured}}}
        assert gate(native["if"], {"release": release}, needs) is runs, (configured, release)
