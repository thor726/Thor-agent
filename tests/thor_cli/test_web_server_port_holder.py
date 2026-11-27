"""The port-holder proof for ``thor gateway migrate --backends`` (Fase 2).

Behaviour contracts only: when a port is (not) proven held by this home's gateway,
and what the old launcher is told. No gateway is started and no socket is bound.
"""

from __future__ import annotations

from thor_cli import web_server_port_holder as holder


def test_port_zero_is_never_held(tmp_path):
    assert holder.gateway_holding_port(0, tmp_path / "home") is None


def test_no_migration_means_no_port_after_migration(tmp_path):
    # No backend_migration.json here, so the marker says the old backend was not
    # retired: the gateway on that port is not reported as a migration holder.
    assert holder.gateway_port_after_migration(9119, tmp_path / "home") is None


def test_binds_overlap_only_in_the_same_address_family():
    assert holder._binds_overlap("127.0.0.1", "127.0.0.1", 9119) is True
    assert holder._binds_overlap("0.0.0.0", "127.0.0.1", 9119) is True  # wildcard takes it
    assert holder._binds_overlap("127.0.0.1", "0.0.0.0", 9119) is True  # wanted wildcard
    assert holder._binds_overlap("127.0.0.1", "127.0.0.2", 9119) is False
    assert holder._binds_overlap("::1", "127.0.0.1", 9119) is False  # across families: unproven
    assert holder._binds_overlap("not-an-address", "127.0.0.1", 9119) is False


def test_listening_addresses_of_no_process_is_empty():
    assert holder._listening_addresses(None, 9119) == []


def test_describe_gateway_holder_tells_the_launcher_to_stop_or_move(tmp_path):
    held = holder.GatewayHolder(control_home=tmp_path / "home", api_origin="http://127.0.0.1:9119",
                                pid=4242, webapp_state="serving", webapp_reason=None,
                                listener_address="http://127.0.0.1:9119")
    lines = holder.describe_gateway_holder(held, "127.0.0.1", 9119)
    text = "\n".join(lines)
    assert "Port 9119 is held by this profile's Thor gateway (PID 4242)" in text
    assert "thor webapp" in text
    assert "--port <other>" in text


def test_launcher_examples_name_the_platform_supervisor():
    assert holder.launcher_examples("win32") == "Task Scheduler task or Startup-folder entry"
    assert holder.launcher_examples("linux") == "systemd unit or launchd job"


def test_gateway_webapp_summary_is_none_without_a_gateway(tmp_path):
    assert holder.gateway_webapp_summary("127.0.0.1", 9119, tmp_path / "home") is None
