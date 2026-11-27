"""Windows facts for ``thor gateway migrate --backends`` (read-only probes).

Pure-function contracts, runnable on any host: Task Scheduler XML matching, .lnk
parsing, Startup-folder script matching, and launcher/child de-duplication. The
psutil process-table scan itself is Windows-only and stays untested here.
"""

from __future__ import annotations

import struct

from thor_cli import gateway_migrate_backends_windows as win

_TASK_XML = """<!-- \\MyTask -->
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Settings><Enabled>true</Enabled></Settings>
  <Actions><Exec>
    <Command>C:\\thor\\thor.exe</Command><Arguments>dashboard --port 9119</Arguments>
  </Exec></Actions>
</Task>
"""


def test_tasks_running_matches_same_install_and_exact_arguments():
    argv = ["C:\\thor\\thor.exe", "dashboard", "--port", "9119"]
    assert win.tasks_running(_TASK_XML, argv) == [("MyTask", True)]

    # Another install with the same arguments is not this backend's task.
    assert win.tasks_running(_TASK_XML, ["D:\\other\\thor.exe", "dashboard", "--port", "9119"]) == []
    # Same install, different arguments is not this backend's task.
    assert win.tasks_running(_TASK_XML, ["C:\\thor\\thor.exe", "dashboard", "--port", "9120"]) == []
    assert win.tasks_running(_TASK_XML, ["C:\\thor\\thor.exe", "serve", "--port", "9119"]) == []


def test_thor_args_and_install_from_entry_token():
    argv = ["C:\\thor\\thor.exe", "dashboard", "--port", "9119"]
    assert win._thor_args(argv) == ["dashboard", "--port", "9119"]
    assert win._install(argv) == "c:\\thor\\thor.exe"
    assert win._thor_args(["python", "-m", "thor_cli.main", "serve", "--port", "9120"]) == [
        "serve", "--port", "9120"]
    assert win._thor_args(["not-thor", "dashboard"]) == []
    assert win._install(["thor", "dashboard"]) is None  # bare name: install unknown


def test_drop_launchers_keeps_only_the_listening_child():
    rows = [(100, "C:\\thor\\thor.exe dashboard --port 9119"),
            (101, "C:\\thor\\thor.exe dashboard --port 9119")]
    # 100 is the launcher (parent of the listening child 101).
    assert win.drop_launchers(rows, ppid_of=lambda pid: {100: 99, 101: 100}[pid]) == [
        (101, "C:\\thor\\thor.exe dashboard --port 9119")]
    assert win.drop_launchers(rows, ppid_of=lambda pid: 99) == rows


def _lnk_bytes(target: str, args: str) -> bytes:
    """Minimal Shell Link: header + LinkInfo local base path + StringData arguments."""
    target_b = target.encode("latin-1") + b"\x00"
    # LinkInfo: size, header size (0x1C: 7 DWORDs), flags, VolumeID offset, LocalBasePath
    # offset, CommonNetworkRelativeLink offset, CommonPathSuffix offset, then the path.
    info = struct.pack("<IIIIIII", 0x1C + len(target_b), 0x1C, 0x01, 0x14, 0x1C, 0, 0) + target_b
    header = bytearray(0x4C)
    struct.pack_into("<I", header, 0, 0x4C)
    struct.pack_into("<I", header, 0x14, 0x02 | 0x20)  # HasLinkInfo + HasArguments
    args_b = args.encode("latin-1")
    return bytes(header) + info + struct.pack("<H", len(args_b)) + args_b


def test_lnk_command_reads_target_and_arguments():
    assert win.lnk_command(_lnk_bytes("C:\\thor\\thor.exe", "dashboard --port 9119")) == [
        "C:\\thor\\thor.exe", "dashboard", "--port", "9119"]
    assert win.lnk_command(b"not a link") is None
    assert win.lnk_command(b"") is None


def test_startup_entries_running_matches_script_command(tmp_path):
    folder = tmp_path / "Startup"
    folder.mkdir()
    (folder / "run-thor.cmd").write_text("@echo off\nC:\\thor\\thor.exe dashboard --port 9119\n",
                                         encoding="utf-8")
    (folder / "other.cmd").write_text("C:\\thor\\thor.exe serve --port 9120\n", encoding="utf-8")
    (folder / "notes.txt").write_text("thor dashboard --port 9119\n", encoding="utf-8")

    hits = win.startup_entries_running(["C:\\thor\\thor.exe", "dashboard", "--port", "9119"],
                                       dirs=[folder])
    assert [h.name for h in hits] == ["run-thor.cmd"]


def test_supervisor_without_scheduler_or_startup_entry_is_manual(monkeypatch):
    monkeypatch.setattr(win, "_schedule_service_pid", lambda: None)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("PROGRAMDATA", raising=False)
    assert win.supervisor(4242, ["C:\\thor\\thor.exe", "dashboard", "--port", "9119"]) == (
        "manual", None, None)
