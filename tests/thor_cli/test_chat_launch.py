"""``thor_cli.chat_launch``: what a plugin's own chat launcher calls around its client process."""
import json
import os
import subprocess

import pytest

from thor_cli.main import PROJECT_ROOT


def test_exit_summary_names_the_launchers_command(tmp_path, monkeypatch, capsys):
    from thor_state import SessionDB
    from thor_cli.chat_launch import print_exit_summary
    home = tmp_path / '.thor'
    home.mkdir()
    monkeypatch.setenv('THOR_HOME', str(home))
    db = SessionDB(db_path=home / 'state.db')
    db.create_session('20261110_120000_abc123', source='tui')
    db.set_session_title('20261110_120000_abc123', 'Demo chat')
    db.append_message('20261110_120000_abc123', 'user', 'q')
    db.append_message('20261110_120000_abc123', 'assistant', 'a')
    db.create_session('20261110_120001_empty0', source='tui')
    db.close()

    print_exit_summary('20261110_120000_abc123', command='thor demo')
    out = capsys.readouterr().out
    assert '  thor demo --resume 20261110_120000_abc123\n' in out
    assert '  thor demo -c "Demo chat"\n' in out
    assert '--tui' not in out

    print_exit_summary('20261110_120001_empty0', command='thor demo')
    assert capsys.readouterr().out == ''


def test_thor_command_runs_this_install_without_pythonpath(tmp_path):
    from thor_cli.chat_launch import thor_command
    home = tmp_path / '.thor'
    home.mkdir()
    (home / 'config.yaml').write_text('updates:\n  check: false\n', encoding='utf-8')
    env = {'THOR_HOME': str(home), 'HOME': str(tmp_path), 'PATH': os.environ.get('PATH', '')}
    child = subprocess.run(thor_command(['--version']), env=env, cwd=str(tmp_path), capture_output=True,
                           text=True, timeout=60, check=False)
    assert child.returncode == 0, child.stderr
    assert child.stdout.startswith('Thor Agent v')
    assert f'Install directory: {PROJECT_ROOT}\n' in child.stdout


@pytest.mark.platforms('windows')  # only Windows publishes the launcher as thor.exe or thor.cmd
def test_thor_command_starts_with_a_file_windows_can_start(tmp_path, monkeypatch):
    from thor_cli import main
    from thor_cli.chat_launch import thor_command
    store = tmp_path / 'store'
    python = store / 'py' / 'python.exe'
    python.parent.mkdir(parents=True)
    python.write_bytes(b'')
    (store / 'facts.json').write_text(json.dumps({'packages': {'python': {'entry': 'py'}}}), encoding='utf-8')
    monkeypatch.setenv('THOR_RUNTIME_DIR', str(store))
    launchers = tmp_path / 'install' / '.thor' / 'bin'
    launchers.mkdir(parents=True)
    monkeypatch.setattr(main, 'PROJECT_ROOT', tmp_path / 'install')

    # Only the batch fallback is published: no child process starts it without a shell.
    (launchers / 'thor.cmd').write_text('@echo off\r\n', encoding='utf-8')
    command = thor_command(['--version'])
    assert os.path.samefile(command[0], python)
    assert command[-1] == '--version'

    (launchers / 'thor.exe').write_bytes(b'MZ')
    command = thor_command(['--version'])
    assert os.path.samefile(command[0], launchers / 'thor.exe')
    assert command[1:] == ['--version']
