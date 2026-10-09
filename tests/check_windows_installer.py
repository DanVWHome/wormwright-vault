"""Check installation and upgrades preserve the tested binary and user data."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
setup = next((root / 'dist-installer').glob('*_setup.exe'))
original = root / 'installer-input/WormwrightVault/WormwrightVault.exe'
with tempfile.TemporaryDirectory(prefix='wormwright-install-') as temp:
    directory = Path(temp)
    installed = directory / 'Programs/Wormwright Vault'
    profile = directory / 'Profile'
    profile.mkdir()
    settings = profile / 'wormwright-vault-beta/locations.json'
    settings.parent.mkdir()
    settings.write_text('{"installer_test":true}')
    vault = directory / 'existing-vault.sqlite'
    vault.write_bytes(b'installer-preservation-test')
    environment = {**os.environ, 'LOCALAPPDATA': str(profile)}
    for _ in range(2):
        subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', f'/DIR={installed}'], env=environment, check=True, timeout=180)
        assert hashlib.sha256((installed / 'WormwrightVault.exe').read_bytes()).digest() == hashlib.sha256(original.read_bytes()).digest()
        assert (installed / 'docs/LICENSE').is_file()
        assert settings.read_text() == '{"installer_test":true}'
        assert vault.read_bytes() == b'installer-preservation-test'
    subprocess.run([sys.executable, str(root / 'tests/smoke_windows_bundle.py'), str(installed / 'WormwrightVault.exe')], check=True, timeout=60)
    # Inno's uninstaller starts a child process; poll for actual removal.
    subprocess.run([str(installed / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], env=environment, check=True, timeout=180)
    import time
    deadline = time.monotonic() + 30
    while (installed / 'WormwrightVault.exe').exists() and time.monotonic() < deadline:
        time.sleep(.25)
    assert not (installed / 'WormwrightVault.exe').exists()
    assert settings.read_text() == '{"installer_test":true}'
    assert vault.read_bytes() == b'installer-preservation-test'
print('PASS: install, upgrade, unchanged binary, startup, uninstall and user-data preservation')
