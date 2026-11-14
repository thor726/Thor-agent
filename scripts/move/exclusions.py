"""Sites the move rewrite leaves alone.

``EXCLUDED`` rows are ``(path, anchor, reason)``; ``BY_HAND`` rows are ``(path, anchor)``: a rewrite inside the
anchored site is flagged as ``by-hand`` instead. An excluded site is neither rewritten nor flagged, and the run
prints each reason once with its site count.

``path`` is the file's path before any move; it also matches the file's new path after this move and the moves
already in the compat MOVES table. ``anchor`` is exact source text: every place it occurs is a site, widened to
the whole statement when it starts a ``def``, ``class``, assignment or ``return``. An empty anchor is the whole file. No line
numbers, so a row holds while the lines around the site shift, and a row whose anchor is gone is flagged.
"""
from __future__ import annotations

import ast

SHIPPED = "called by shipped updaters and installers of earlier releases"
PERSISTED = "text persisted into units, launchers, desktop entries and the Codex MCP config that outlive this tree"
IDENTITY = "matches processes started before the move by their old command line"
FROZEN = "frozen code for historical updaters"
TORN_UPDATE = "torn-update fallback that reads the directory a killed update moved aside"
OLD_NAMES = "a test of how old top-level names resolve, so it names them on purpose"
KEPT_NAMES = (SHIPPED, PERSISTED, IDENTITY)
"""Reasons whose sites keep module names that tests may mirror: those names are flagged in test argv, not rewritten."""

EXCLUDED: tuple[tuple[str, str, str], ...] = (
    ("thor_cli/_old_updater.py", "", FROZEN),
    ("tests/compat/old_updater_dependencies.py", "", FROZEN),
    ("thor_cli/_launchers.py", "def runtime_command(", PERSISTED),
    ("thor_cli/_launchers.py", '_CLOSURE_REPAIR = """\\', PERSISTED),
    ("thor_cli/_launchers.py", "return (\n        # The repair's own stdlib", PERSISTED),
    ("thor_cli/_launchers.py", "def print_runtime_command(", PERSISTED),
    ("thor_bootstrap.py", "def _settle_interrupted_update(", TORN_UPDATE),
    (".github/actions/plugin-validate/action.yml", '"$_VALIDATOR_PYTHON" -I -m thor_cli.main plugins validate "$_PLUGIN_PATH"', SHIPPED),
    ("apps/bootstrap-installer/src-tauri/src/update.rs", 'if install_root.join("thor_cli/_launchers.py").is_file() {', SHIPPED),
    ("apps/desktop/electron/desktop-uninstall.ts", "return ['-m', 'thor_cli.uninstall', '--mode', mode]", SHIPPED),
    ("apps/desktop/electron/main.ts", "return directoryExists(root) && fileExists(path.join(root, 'thor_cli', 'main.py'))", SHIPPED),
    ("apps/desktop/electron/main.ts", "script: path.join(root, 'thor_cli', 'backup_sqlite.py'),", SHIPPED),
    ("apps/desktop/electron/main.ts", "['-m', 'thor_cli.main', 'uninstall', '--gui-summary'],", SHIPPED),
    ("apps/desktop/electron/source-backend.ts", "if (!existsSync(path.join(root, 'thor_cli', 'main.py'))) {", SHIPPED),
    ("apps/desktop/electron/source-backend.ts", "args: ['-m', 'thor_cli.main', ...args],", SHIPPED),
    ("apps/desktop/electron/updater-process.ts", "if (!stagedFileExists(path.join(updateRoot, 'thor_cli', '_launchers.py'))) {", SHIPPED),
    ("apps/desktop/electron/updater-process.ts", "if (root && existsSync(path.join(root, 'thor_cli', 'main.py'))) {", SHIPPED),
    ("apps/desktop/electron/updater/checkout-source.ts", "? ['--run-module', 'thor_cli.source_check']", SHIPPED),
    ("apps/desktop/electron/updater/checkout-source.ts", "'from pathlib import Path; import runpy; p = Path(\"thor_cli/source_check.py\"); entry = runpy.run_path(str(p)).get(\"main\") if p.is_file() else None; entry() if callable(entry) else print(\"null\")'", SHIPPED),
    ("apps/desktop/electron/updater/state-db-preflight.ts", "const args: string[] = launcher ? ['--run-module', 'thor_cli.backup_sqlite', home] : ['-I', '-S', script, home]", SHIPPED),
    ("apps/desktop/electron/windows-thor-path.ts", "args: ['-m', 'thor_cli.main', ...backendArgs],", SHIPPED),
    ("apps/desktop/electron/windows-runtime-command.ts", "return [runtime.thorPath, '--run-module', 'thor_cli.windows_ssh_runtime', operation, ...args]", SHIPPED),
    ("gateway/status.py", "def _read_process_cmdline(", IDENTITY),
    ("gateway/status.py", "def _record_looks_like_gateway(", IDENTITY),
    ("gateway/status.py", "def profile_flag_value(", IDENTITY),
    ("gateway/status.py", "def _record_matches_live_gateway_pid(", IDENTITY),
    ("thor_cli/_launchers.py", "def installation_command(", PERSISTED),
    ("thor_cli/_launchers.py", '"thor": ("thor_cli.main", "main"),', PERSISTED),
    ("thor_cli/_launchers.py", '"thor-acp": ("acp_adapter.entry", "main"),', PERSISTED),
    ("thor_cli/_launchers.py", '"        from thor_cli import _early_recovery\\n"', PERSISTED),
    ("thor_cli/_launchers.py", '"    from thor_cli._launchers import print_runtime_command\\n"', PERSISTED),
    ("thor_cli/_launchers.py", '"    import thor_bootstrap\\n"', PERSISTED),
    ("thor_cli/_launchers.py", 'command = ([str(root / ".thor/bin/thor"), "--run-module", "run_agent"]', PERSISTED),
    ("thor_cli/_subprocess_compat.py", "def _text_names_thor(", IDENTITY),
    ("thor_cli/codex_runtime_plugin_migration.py", '"args": ["-P", "-m", "agent.transports.thor_tools_mcp_server"],',
     PERSISTED),
    ("thor_cli/container_boot.py", 'if any("main-wrapper.sh" in part for part in argv):', IDENTITY),
    ("thor_cli/dashboard_procs.py", "def _dashboard_subcommand_index(", IDENTITY),
    ("thor_cli/data_cleanup.py", 'if (canonical / "thor_cli" / "__init__.py").is_file():', SHIPPED),
    ("thor_cli/gateway.py", 'if (parent.name() or "").lower() == "services.exe":', IDENTITY),
    ("thor_cli/gateway.py", "_LEGACY_UNIT_EXECSTART_MARKERS: tuple[str, ...] = (", IDENTITY),
    ("thor_cli/gateway.py", 'cleanup = installation_command(project_root, module="gateway.cgroup_cleanup",', PERSISTED),
    ("thor_cli/gateway.py", 'stop_mark = installation_command(project_root, module="gateway.systemd_stop_mark",', PERSISTED),
    ("thor_cli/gateway_connections_ssh_remote.py", 'raw=open(f"/proc/{{pid}}/cmdline","rb").read()', IDENTITY),
    ("thor_cli/gateway_launchd.py", 'module="thor_cli.stderr_timestamp", python=_gw().get_python_path())', PERSISTED),
    ("thor_cli/gateway_windows.py", 'argv = [python_exe, "-m", "thor_cli.main"]', PERSISTED),
    ("thor_cli/linux_desktop_entry.py", 'argv = [interpreter, "-m", "thor_cli.main", *_desktop_argv_tail(project_root)]', PERSISTED),
    ("thor_cli/main_dashboard.py", "if cmdline is not None and _norm(list(cmdline)) == _norm(argv):", IDENTITY),
    ("thor_cli/main_desktop.py", "return release_dir in Path(proc.exe()).resolve().parents", IDENTITY),
    ("thor_cli/main_desktop.py", 'exe = proc.info.get("exe") or ""', IDENTITY),
    ("thor_cli/source_completion.py", 'if not (root / "thor_cli/source_completion.py").is_file():', SHIPPED),
    ("thor_cli/update_cmd_windows.py", '"thor_cli.main" in cmdline_low and (root_prefix in cmdline_low or _cwd_prefix(proc).startswith(root_prefix))', IDENTITY),
    ("thor_cli/update_cmd_windows.py", 'return "thor_cli.main" in (cmdline or "").lower() and _thor_holder_subcommand(cmdline) in _BACKEND_PURPOSES', IDENTITY),
    ("thor_cli/update_completion.py", 'str(root / "thor_cli/update_completion.py"),', SHIPPED),
    ("thor_cli/update_handoff.py", 'return [str(post_swap_python()), "-m", "thor_cli.main", "update", *argv_tail,', SHIPPED),
    ("thor_cli/update_owning_install.py", 'owner = venv.parent if (venv.parent / "thor_cli" / "main.py").is_file() else _pm_environment_owner(venv)', SHIPPED),
    ("thor_cli/update_owning_install.py", 'if install_key(owner) != state.name or not (owner / "thor_cli" / "main.py").is_file():', SHIPPED),
    ("thor_cli/update_owning_install.py", 'code = subprocess.call([sys.executable, "-m", "thor_cli.main", *sys.argv[1:]], cwd=owner, env=env)', SHIPPED),
    ("thor_state_holders.py", "def _argv_scoped_to_other_home(", IDENTITY),
    ("scripts/code_health/py_rules.py", "def argv_identity(", IDENTITY),
    ("scripts/desktop-update/posix.sh", 'UPDATE_INVOKE=("$bin/python" -m thor_cli.main)', SHIPPED),
    ("scripts/desktop-update/posix.sh", 'if [ -f "$INSTALL_ROOT/thor_cli/_launchers.py" ]; then', SHIPPED),
    ("scripts/desktop-update/runtime.ps1", "[string]$Module = 'thor_cli.main'", SHIPPED),
    ("scripts/desktop-update/runtime.ps1", "if (Test-Path -LiteralPath (Join-Path $InstallRoot 'thor_cli/_launchers.py') -PathType Leaf) {", SHIPPED),
    ("scripts/desktop-update/windows.ps1", "$verifyCommand = @(Get-ThorRuntimeCommand -InstallRoot $InstallRoot -Module 'thor_cli.desktop_update_verify')", SHIPPED),
    ("scripts/install.ps1", "$completionArgs = @('-I', '-B', '-X', 'utf8', 'thor_cli/source_completion.py', '--source', $InstallDir)", SHIPPED),
    ("scripts/install.ps1", 'Invoke-Logged "Publishing the thor command" { & $bootPy -I -X utf8 thor_cli/_launchers.py $binDir }', SHIPPED),
    ("scripts/install.sh", '"$boot_py" -I -B -X utf8 thor_cli/source_completion.py "${args[@]}") \\', SHIPPED),
    ("setup-thor.sh", 'if ! "$boot_py" -I -X utf8 thor_cli/_launchers.py "$bin_dir"; then', SHIPPED),
    ("tests/thor_cli/test_stale_root_module_bridge.py", "def pre_handoff_purge(", OLD_NAMES),
    ("tests/test_thor_bootstrap.py", 'program = r"""\nimport importlib.util, os, sys\nfrom importlib.abc import MetaPathFinder', OLD_NAMES),
    ("tools/bot_desktop/runtime.py", 'Path(project_root_str()), module="tools.bot_desktop.idle_watch")),', SHIPPED),
    ("tools/mcp_tool_lifecycle.py", '"tui_gateway.slash_worker", "tui_gateway.entry",', IDENTITY),
    ("tui_gateway/host_supervisor.py", 'return "tui_gateway.compute_host" in _pid_command(pid)', IDENTITY),
    ("scripts/build/launcher_wrapper.py", 'importlib.import_module("thor_bootstrap")', PERSISTED),
)

BY_HAND: tuple[tuple[str, str], ...] = (
    ("cron/lifecycle_guard.py", 'r"|(?:\\b(?:p?kill|taskkill|stop-process)\\b[^\\n]*\\bthor\\b[^\\n]*\\bgateway)"'),
    ("cron/lifecycle_guard.py", '_GATEWAY_CMDLINE_TOKEN_RE = re.compile(r"(?i)thor_cli|\\bthor\\b[^\\n]*\\bgateway\\b|\\bgateway\\b[^\\n]*\\bthor\\b")'),
    ("gateway/status.py", "def _gateway_command_subcommand("),
    ("gateway/status.py", 'entry = sys.modules.get("thor_cli.main")'),
    ("gateway/status_inline_source.py", 'r"\\s*from\\s+(?P<target>thor_cli\\.main)\\s+import\\s+main\\s*;\\s*sys\\.exit\\(\\s*main\\(\\)\\s*\\)")),'),
    ("thor_cli/gateway_runtime_service_identity.py", "module = next((name for name in ("),
    ("thor_cli/profiles.py", "_THOR_ARGV_MARKERS = ("),
    ("thor_cli/update_cmd_windows.py", "def _is_entry("),
    ("thor_cli/update_receipt.py", 'if (parent / "thor_cli" / "main.py").is_file():'),
    ("thor_cli/windows_ssh_runtime.py", 'launches_module = logical_argv[1:3] == ["-m", "thor_cli.main"]'),
    ("thor_state_holders.py", "_THOR_PYTHON_MODULES = frozenset({"),
    ("tools/skill_lock.py", 'if verb == "thor" or (verb.startswith("python") and "thor_cli.main" in args):'),
)


def anchor_spans(source: str, anchor: str) -> list[tuple[int, int]]:
    """First and last line of every site ``anchor`` marks in ``source``."""
    if not anchor:
        return [(1, source.count("\n") + 1)]
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    statements: dict[tuple[int, int], int] = {}
    for node in ast.walk(tree) if tree is not None else ():
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign,
                             ast.Return)):
            key = (node.lineno, node.col_offset)
            statements[key] = max(statements.get(key, 0), node.end_lineno or node.lineno)
    spans, at = [], source.find(anchor)
    while at >= 0:
        line = source.count("\n", 0, at) + 1
        column = len(source[source.rfind("\n", 0, at) + 1:at].encode("utf-8"))
        spans.append((line, max(line + anchor.count("\n"), statements.get((line, column), 0))))
        at = source.find(anchor, at + 1)
    return spans
