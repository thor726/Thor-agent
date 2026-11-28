"""Tag pages and release bodies publish the same independently named objects."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote
from urllib.request import urlopen

import pytest

from tests.scripts.release_fakes import page_bytes, page_keys, release_transport

_SPEC = importlib.util.spec_from_file_location(
    'render_builds_table', Path(__file__).resolve().parents[2] / 'scripts/render-builds-table.py')
assert _SPEC and _SPEC.loader
rbt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rbt)


def seed(worktree, key, data):
    path = Path(worktree).joinpath(*key.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def snapshot(worktree):
    return {key: page_bytes(worktree, key) for key in page_keys(worktree)}


@pytest.fixture
def release_body(monkeypatch):
    state = {'body': '# Notes\n\n<!-- THOR_BUILDS_TABLE -->\n\n## Changes\n- x\n', 'edits': []}

    real_run = subprocess.run

    def gh(argv, **kwargs):
        if argv[:1] != ['gh']:
            return real_run(argv, **kwargs)
        if argv[:3] == ['gh', 'release', 'view']:
            return subprocess.CompletedProcess(argv, 0, json.dumps({'body': state['body']}), '')
        assert argv[:3] == ['gh', 'release', 'edit']
        state['body'] = kwargs['input']
        state['edits'].append(state['body'])
        return subprocess.CompletedProcess(argv, 0, '', '')

    monkeypatch.setattr(rbt.subprocess, 'run', gh)
    return state


@pytest.mark.parametrize('tag', ['v1.2.3', 'v1.2.3+canary.20260818T101010Z'])
def test_tag_publication_pending_rerun_stale_and_dry_run(monkeypatch, release_transport, release_body, tag):
    worktree, base = release_transport.worktree, release_transport.base
    version = tag[1:]
    prefix = f'releases/tag/{tag}/'
    visible = [f'ThorBundled-{version}-mac-arm64.dmg', f'ThorBundled-{version}-win-x64.msix',
               f'ThorBundled-{version}-win-arm64.msix', f'ThorBundled-{version}-linux-x64.AppImage',
               f'ThorLight-{version}-win-x64.msix']
    hidden = [f'ThorBundled-{version}-mac-arm64.zip', f'ThorBundled-{version}-win.msixbundle',
              f'ThorBundled-{version}-win-x64.msix.blockmap', 'latest.yml',
              'ThorBundled-9.9.9-win-x64.msix']
    for name in visible + hidden:
        seed(worktree, prefix + name, name.encode())
    seed(worktree, 'releases/tag/v9.9.9/ThorBundled-9.9.9-win-x64.msix', b'neighbor')
    monkeypatch.setenv('RELEASE_NEEDS', '{"build-win32":{"result":"success"}}')
    args = ['render-builds-table.py', '--tag', tag, '--repo', 'o/r', '--r2-base-url', base + '/']

    def render(*extra):
        monkeypatch.setattr(sys, 'argv', [*args, *extra])
        assert rbt.main() == 0

    for run in ('1', '2'):
        render('--pending-run-url', f'https://github.example/runs/{run}')
    assert 'runs/1' not in release_body['body'] and release_body['body'].count('runs/2') == 1
    assert page_bytes(worktree, prefix + 'index.html') is None
    render()
    body = release_body['body']
    assert 'runs/2' not in body and body.count('## Downloads') == 1
    assert body.count(rbt.MARKER) == body.count(rbt.END_MARKER) == 1
    expected = {rbt.pages.public_url_for(base, prefix + name) for name in visible}
    assert set(re.findall(r'\]\((http[^)]+)\)', body)) == expected
    with urlopen(f'{base}/{prefix}index.html', timeout=5) as response:
        page = response.read().decode()
    release_url = rbt.pages.public_url_for('https://github.com/o/r/releases/tag', tag)
    assert set(re.findall(r'href="(http[^"]+)"', page)) == expected | {release_url}
    assert rbt.recorded_build(page) == tag and 'Bundle environment' not in page
    assert all(name not in page and name not in body for name in hidden)
    assert 'linux-arm64' not in page
    for url in expected:
        with urlopen(url, timeout=5) as response:
            assert response.read() == unquote(url.rsplit('/', 1)[1]).encode()
    channel_key = 'releases/canary/index.html' if '+canary.' in tag else 'releases/stable/index.html'
    assert page_bytes(worktree, channel_key).decode() == page
    render()
    assert release_body['body'] == body

    # Use the real page writer's marker format, independent of asset selection.
    newer = rbt.render_page('v9.9.9', {}, base).encode()
    seed(worktree, channel_key, newer)
    render()
    assert page_bytes(worktree, channel_key) == newer
    assert page_bytes(worktree, prefix + 'index.html').decode() == page
    before, edits = snapshot(worktree), list(release_body['edits'])
    render('--dry-run')
    assert snapshot(worktree) == before and release_body['edits'] == edits
    release_body['body'] = 'no marker here'
    render()
    assert release_body['body'] == 'no marker here' and release_body['edits'] == edits

    # A release that does not serve the channel (--only windows,docker) renders its own page and
    # table but leaves the shared downloads page alone; the same page is replaced without the flag.
    release_body['body'] = rbt.MARKER
    older = rbt.render_page('v1.2.3+canary.20200101T000000Z' if '+canary.' in tag else 'v0.0.1', {}, base).encode()
    seed(worktree, channel_key, older)
    render('--no-channel-page')
    assert page_bytes(worktree, channel_key) == older
    release_body['body'] = rbt.MARKER
    render()
    assert page_bytes(worktree, channel_key).decode() == page


@pytest.mark.parametrize('asset_present', [False, True])
@pytest.mark.parametrize('result', ['failure', 'cancelled', 'skipped'])
def test_incomplete_tag_keeps_channel_and_links_diagnostics(monkeypatch, release_transport, release_body, asset_present, result):
    worktree, base = release_transport.worktree, release_transport.base
    tag = 'v1.2.3+canary.20260818T101010Z'
    key = f'releases/tag/{tag}/ThorBundled-{tag[1:]}-win-x64.msix'
    seed(worktree, 'releases/canary/index.html', b'previous good page')
    if asset_present:
        seed(worktree, key, b'transport fixture')
    run = 'https://github.example/runs/123'
    monkeypatch.setenv('RELEASE_NEEDS', json.dumps({'publish-win32-updater': {'result': result}}))
    monkeypatch.setattr(sys, 'argv', ['renderer', '--tag', tag, '--r2-base-url', base, '--run-url', run])
    assert rbt.main() == 0
    with urlopen(f'{base}/releases/tag/{tag}/index.html', timeout=5) as response:
        page = response.read().decode()
    for output in (page, release_body['body']):
        assert 'Build incomplete' in output and f'publish-win32-updater ({result})' in output
        assert run in output
        assert (rbt.pages.public_url_for(base, key) in output) == asset_present
    assert ('No downloadable artifacts' in page) == (not asset_present)
    assert page_bytes(worktree, 'releases/canary/index.html') == b'previous good page'


def test_attempt_page_warns_and_canary_page_does_not():
    base = 'https://cdn.example'
    sentence = ('Attempt builds are not upgrade-safe: every attempt of 1.2.3 has the same '
                'package version, so an installed attempt is not replaced by the published 1.2.3.')
    page = rbt.render_page('rc.1-v1.2.3', {}, base)
    assert sentence in page
    for tag in ('v1.2.3', 'v1.2.3+canary.20260818T101010Z', 'abandoned-rc.1-v1.2.3'):
        assert sentence not in rbt.render_page(tag, {}, base)


@pytest.mark.parametrize('version,name', [
    ('1.2.3', 'ThorBundled-1.2.3-win-x64.msix'),
    ('1.2.3+canary.20260818T000000Z', 'ThorBundled-1.2.3+canary.20260818T000000Z-win-x64.msix'),
])
def test_exact_version_and_flat_name_boundaries(version, name):
    names = [name, 'ThorBundled-1.2.3+canary.20260817T000000Z-win-x64.msix', 'ThorBundled-1.2.4-win-x64.msix', name + '.blockmap']
    assert rbt.filter_names_for_version(names, version) == [name]
    assert rbt.parse_assets([name])['ThorBundled'][('win', 'x64')] == (name, 'msix')


def test_attempt_archive_objects_are_listed_by_their_plain_version(monkeypatch):
    keys = ['releases/tag/rc.2-v1.2.3/ThorBundled-1.2.3-win-x64.msix',
            'releases/tag/rc.2-v1.2.3/ThorBundled-1.2.3-win-x64.msix.blockmap',
            'releases/tag/rc.2-v1.2.3/latest.yml',
            'releases/tag/rc.2-v1.2.3/ThorBundled-1.2.4-win-x64.msix']
    monkeypatch.setattr(rbt, 'r2_object_names_under', lambda prefix: keys)
    assert rbt.r2_object_names('rc.2-v1.2.3') == [keys[0]]


@pytest.mark.parametrize('current,tag,allowed', [
    (None, 'v1.2.3', True), ('garbage', 'v1.2.3', True),
    ('v1.2.3', 'v1.2.3+canary.20260818T101010Z', False),
    ('v1.2.3+canary.20260818T101010Z', 'v1.2.3+canary.20260818T101009Z', False),
    ('v1.2.3+canary.20260818T101010Z', 'v1.2.3+canary.20260818T101011Z', True),
])
def test_channel_order_boundaries(current, tag, allowed):
    page = rbt.render_page(current, {}, 'https://cdn.example') if current and current != 'garbage' else current
    assert rbt.supersedes(page, tag) is allowed
