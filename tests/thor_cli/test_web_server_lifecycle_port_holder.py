"""After a backend migration, the old command never starts beside the gateway on the gateway's port
(Fase 4, adaptasi A9 / jalur konflik bind).

macOS lets ``thor dashboard --port P`` bind ``127.0.0.1:P`` while the gateway listens on ``*:P`` (the more
specific address wins for loopback clients), so the bind probe alone let the retired backend come back as a
second session owner. With the migration's manifest saying the old backend is retired, the probe reports a
conflict whatever the OS would allow, and the report names the gateway and exits 78; without one nothing
changes. Behaviour contracts only: no gateway is started, no socket is bound by the probe tests except the
free-port check's own probe.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from thor_cli import web_server_port_holder as holder
from thor_cli.web_server_lifecycle import (
    PORT_IN_USE_EXIT_CODE,
    _port_bind_conflict,
    _report_port_in_use,
)


def _fake_holder(port: int) -> holder.GatewayHolder:
    return holder.GatewayHolder(
        control_home=Path("/tmp/thor-home"), api_origin=f"http://127.0.0.1:{port}",
        pid=4242, webapp_state="serving", webapp_reason=None,
        listener_address=f"http://127.0.0.1:{port}")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_a_free_port_conflicts_when_the_gateway_holds_it_after_a_migration(monkeypatch):
    """The OS would allow the bind, but the migration holder makes it a conflict."""
    port = _free_port()
    monkeypatch.setattr(holder, "gateway_port_after_migration", lambda p, home=None: _fake_holder(p))
    assert _port_bind_conflict("127.0.0.1", port) is True
    assert _port_bind_conflict("127.0.0.2", port) is True  # another address of the same port


def test_a_free_port_is_clean_without_a_migration(monkeypatch):
    port = _free_port()
    monkeypatch.setattr(holder, "gateway_port_after_migration", lambda p, home=None: None)
    assert _port_bind_conflict("127.0.0.1", port) is False


def test_ephemeral_port_zero_never_conflicts(monkeypatch):
    def must_not_be_asked(port, home=None):
        raise AssertionError("port 0 must short-circuit")

    monkeypatch.setattr(holder, "gateway_port_after_migration", must_not_be_asked)
    assert _port_bind_conflict("127.0.0.1", 0) is False


def test_the_report_names_the_gateway_holder_and_exits_78(monkeypatch, capfd):
    """The sentinel line is always first; the holder hint replaces the generic one; code is EX_CONFIG."""
    port = _free_port()
    monkeypatch.setattr(holder, "gateway_holding_port", lambda p, home=None, host=None: _fake_holder(p))
    monkeypatch.setattr(holder, "gateway_port_after_migration", lambda p, home=None: None)
    assert _report_port_in_use("127.0.0.1", port) == 78
    out = capfd.readouterr().out
    assert out.splitlines()[0] == f"BACKEND_PORT_IN_USE port={port}"
    assert f"Port {port} is held by this profile's Thor gateway (PID 4242)" in out
    assert "the gateway serves the Webapp" in out
    assert "likely another 'thor serve'" not in out


def test_the_report_names_the_gateway_after_a_migration_even_for_another_address(monkeypatch, capfd):
    """After a migration the gateway on *port* is the holder for any address of that port."""
    port = _free_port()
    monkeypatch.setattr(holder, "gateway_holding_port", lambda p, home=None, host=None: None)
    monkeypatch.setattr(holder, "gateway_port_after_migration", lambda p, home=None: _fake_holder(p))
    assert _report_port_in_use("127.0.0.2", port, headless=True) == 78
    out = capfd.readouterr().out
    assert f"Port {port} is held by this profile's Thor gateway (PID 4242)" in out
    assert "`thor serve` is no longer needed here" in out


def test_without_a_holder_the_report_keeps_the_generic_hint_and_exit_75(monkeypatch, capfd):
    port = _free_port()
    monkeypatch.setattr(holder, "gateway_holding_port", lambda p, home=None, host=None: None)
    monkeypatch.setattr(holder, "gateway_port_after_migration", lambda p, home=None: None)
    assert _report_port_in_use("127.0.0.1", port) == PORT_IN_USE_EXIT_CODE
    out = capfd.readouterr().out
    assert out.splitlines()[0] == f"BACKEND_PORT_IN_USE port={port}"
    assert "likely another 'thor serve' / 'thor dashboard' backend or the Thor gateway" in out
    assert "held by this profile's Thor gateway" not in out
