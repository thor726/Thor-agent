"""App Installer descriptors bind explicit package facts to explicit feed URLs."""
import xml.etree.ElementTree as ET

import pytest

from scripts.bundles import release_artifacts as artifacts
from scripts.releases import pages
from tests.scripts.release_fakes import page_bytes, release_transport


@pytest.mark.parametrize('variant', ['bundled', 'light'])
def test_canary_publication_verifies_native_identity_and_uploads_bundle_before_pointer(tmp_path, release_transport, monkeypatch, variant):
    import zipfile

    worktree = release_transport.worktree
    tag, version = 'v1.2.4+canary.20260902T000000Z', '1.2.4.1440'
    identity, publisher = f'Fixture.{variant}.Canary', 'CN=Fixture & Team'
    bundle = tmp_path / 'app.msixbundle'
    manifest = ET.Element('Bundle')
    ET.SubElement(manifest, 'Identity', {'Name': identity, 'Publisher': publisher, 'Version': version})
    with zipfile.ZipFile(bundle, 'w') as archive:
        archive.writestr('AppxMetadata/AppxBundleManifest.xml', ET.tostring(manifest))
    base = 'https://releases.example'
    directory = f"releases/win32/{'light/' if variant == 'light' else ''}canary"
    pointer = f'{directory}/canary.appinstaller'
    args = ['publish-appinstaller', '--root', str(tmp_path), '--tag', tag, '--variant', variant,
            '--bundle', str(bundle), '--identity', identity, '--publisher', publisher, '--version', version,
            '--public-base', base]
    puts = []
    original_put = pages.put
    def recording_put(**kwargs):
        puts.append(kwargs["key"])
        return original_put(**kwargs)
    monkeypatch.setattr(pages, "put", recording_put)
    artifacts.main(args)
    assert page_bytes(worktree, f'{directory}/{bundle.name}') == bundle.read_bytes()
    descriptor = ET.fromstring(page_bytes(worktree, pointer))
    assert descriptor.attrib == {'Uri': f'{base}/{pointer}', 'Version': version}
    assert descriptor.find('{*}MainBundle').attrib == {
        'Name': identity, 'Publisher': publisher, 'Version': version, 'Uri': f'{base}/{directory}/{bundle.name}',
    }
    # The bundle lands before the pointer that names it.
    assert puts.index(f'{directory}/{bundle.name}') < puts.index(pointer)
    previous = page_bytes(worktree, pointer)
    for option, bad in [('--identity', 'Wrong'), ('--publisher', 'CN=Wrong'), ('--version', '9.9.9.0'),
                        ('--tag', 'v1.2.4'), ('--tag', 'a' * 40), ('--variant', 'store')]:
        invalid = list(args)
        invalid[invalid.index(option) + 1] = bad
        puts.clear()
        with pytest.raises((ValueError, SystemExit)):
            artifacts.main(invalid)
        assert not puts
        assert page_bytes(worktree, pointer) == previous

    # Fail a real immutable upload by occupying its name with different bytes.
    occupied = worktree.joinpath(*f'{directory}/{bundle.name}'.split("/"))
    occupied.write_bytes(b'other bundle')
    puts.clear()
    with pytest.raises(ValueError, match='immutable'):
        artifacts.main(args)
    assert pointer not in puts
    assert page_bytes(worktree, pointer) == previous
