"""Exercise the Qt control adapter with separate processes and dummy paths."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtCore import QCoreApplication, QTimer
from windows_control import LocalControl, send

if len(sys.argv) > 1:
    app = QCoreApplication([])
    calls = []
    def callback(request):
        calls.append(request)
        if request['action'] == 'lock':
            QTimer.singleShot(250, app.quit)
    control = LocalControl(Path(sys.argv[1]), callback)
    try:
        LocalControl(Path(sys.argv[1]), callback)
        raise AssertionError('Duplicate instance accepted')
    except RuntimeError:
        pass
    timer = QTimer(); timer.timeout.connect(control.poll); timer.start(10)
    QTimer.singleShot(10000, app.quit)
    print('ready', flush=True)
    app.exec(); control.close()
    assert [r['action'] for r in calls] == ['lookup', 'lock']
else:
    with tempfile.TemporaryDirectory() as directory:
        vault = Path(directory) / 'dummy vault.sqlite'
        child = subprocess.Popen([sys.executable, __file__, str(vault)], stdout=subprocess.PIPE, text=True)
        try:
            assert child.stdout.readline().strip() == 'ready'
            result = send(vault, {'version': 1, 'action': 'capabilities'})
            assert result['returns_secrets'] is False
            assert send(vault, {'version': 1, 'action': 'lookup', 'query': 'dummy'})['accepted']
            assert send(vault, {'version': 1, 'action': 'lock'})['accepted']
            assert child.wait(timeout=15) == 0
            try:
                send(vault, {'version': 1, 'action': 'open'})
                raise AssertionError('Closed server accepted request')
            except ConnectionRefusedError:
                pass
        finally:
            if child.poll() is None:
                child.kill(); child.wait()
    print('PASS: Qt control routing, duplicate lock and shutdown.')
