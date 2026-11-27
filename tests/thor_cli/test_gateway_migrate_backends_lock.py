"""The run lock for ``thor gateway migrate --backends`` (Fase 2).

Behaviour contracts only: one holder per home, a kernel lock that dies with its
holder, and the ``--status`` command a loser is told to watch.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tests.waiting import wait_until
from thor_cli import gateway_migrate_backends_lock as lock


def test_acquire_release_reacquire_in_one_process(tmp_path):
    home = tmp_path / "home"
    try:
        assert lock.acquire(home) is True
        assert lock.holder_pid(home) == os.getpid()
        assert lock.acquire(home) is True  # re-entrant in the holder
        lock.release()
        assert lock.acquire(home) is True
    finally:
        lock.release()


def test_busy_message_names_the_thor_status_command(tmp_path):
    home = tmp_path / "home"
    message = lock.busy_message(home)
    assert "thor gateway migrate --backends --status" in message
    assert "already running" in message


def test_ack_roundtrip_reports_whether_the_background_run_got_the_lock(tmp_path):
    home = tmp_path / "home"
    token = lock.new_ack_token()
    assert token.isalnum()
    lock.write_ack(home, token, locked=True)
    ack = lock.wait_ack(home, token, seconds=1)
    assert ack is not None and ack["locked"] is True and ack["pid"] == os.getpid()
    assert lock.wait_ack(home, token, seconds=0) is None  # consumed


def test_prune_stale_acks_removes_only_abandoned_ones(tmp_path):
    home = tmp_path / "home"
    token = lock.new_ack_token()
    lock.write_ack(home, token, locked=False)
    stale = home / "backend_migration" / f"detach-ack-{token}.json"
    old = time.time() - lock.ACK_WAIT_SECONDS - 60
    os.utime(stale, (old, old))
    lock.prune_stale_acks(home)
    assert not stale.exists()


def test_a_second_process_cannot_acquire_while_the_first_holds_it(tmp_path):
    home = tmp_path / "home"
    ready = tmp_path / "holder-ready"
    root = Path(__file__).resolve().parents[2]
    child = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, threading; sys.path.insert(0, sys.argv[1]); "
         "from thor_cli import gateway_migrate_backends_lock as lock; "
         "assert lock.acquire(__import__('pathlib').Path(sys.argv[2])); "
         "open(sys.argv[3], 'w').write('held'); threading.Event().wait(30)",
         str(root), str(home), str(ready)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THOR_HOME": str(home)})
    try:
        wait_until(lambda: ready.exists(), timeout=15, what="the holder child to take the lock")
        lock.release()  # this process holds nothing; make the re-entrancy guard inert
        assert lock.acquire(home) is False
        assert lock.holder_pid(home) == child.pid
    finally:
        lock.release()
        child.terminate()
        child.wait(timeout=10)
    assert lock.acquire(home) is True  # the kernel dropped the dead holder's lock
    lock.release()
