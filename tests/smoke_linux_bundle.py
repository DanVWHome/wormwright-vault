"""Check installed Linux app startup without touching a real vault or key."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hooks import send

executable = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='wormwright-rpm-') as directory:
    vault = Path(directory) / ('long-vault-location-' * 8) / 'invented.sqlite'
    vault.parent.mkdir()
    environment = {**os.environ, 'XDG_DATA_HOME': directory, 'XDG_RUNTIME_DIR': str(vault.parent),
                   'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'xcb')}
    # The client must resolve the same runtime socket as the child.
    os.environ['XDG_RUNTIME_DIR'] = environment['XDG_RUNTIME_DIR']
    child = subprocess.Popen([str(executable), str(vault)], env=environment)
    try:
        deadline = time.monotonic() + 40
        while True:
            if child.poll() is not None:
                raise RuntimeError('Installed application exited before startup')
            try:
                result = send(vault, {'version': 1, 'action': 'capabilities'})
                assert result['returns_secrets'] is False
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if time.monotonic() > deadline:
                    raise RuntimeError('Installed application did not start')
                time.sleep(.25)
        assert send(vault, {'version': 1, 'action': 'lock'})['accepted']
        assert not vault.exists(), 'Startup must not create a personal vault implicitly'
        print('PASS: installed Fedora app starts with a long vault/runtime path, local control responds, no user vault changed')
    finally:
        child.terminate(); child.wait(timeout=15)
