"""Check the packaged app starts and responds without using an existing vault."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from windows_control import send

executable = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='wormwright-bundle-') as directory:
    vault = Path(directory) / 'dummy.sqlite'
    environment = {**os.environ, 'LOCALAPPDATA': directory, 'QT_QPA_PLATFORM': 'offscreen'}
    child = subprocess.Popen([str(executable), str(vault)], env=environment)
    try:
        deadline = time.monotonic() + 30
        while True:
            if child.poll() is not None:
                raise RuntimeError('Packaged app exited before startup')
            try:
                result = send(vault, {'version': 1, 'action': 'capabilities'})
                assert result['returns_secrets'] is False
                break
            except ConnectionRefusedError:
                if time.monotonic() > deadline:
                    raise RuntimeError('Packaged app did not start')
                time.sleep(.25)
        assert send(vault, {'version': 1, 'action': 'lock'})['accepted']
        print('PASS: packaged Windows app startup and local UI control')
    finally:
        child.terminate(); child.wait(timeout=15)
