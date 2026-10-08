"""Synthetic Windows startup persistence, native-key routing and small screens."""
from pathlib import Path
import os
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
import managed_locations
import yubikey_auth
from sync import configure, read_settings
from managed_vault import ManagedVault
from key_ui import request_key_pin
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from managed_ui import ManagedWindow
from window_geometry import fit_to_screen

if sys.platform == 'win32':
    from fido2.client.windows import WindowsClient
    assert WindowsClient.is_available(), 'Native Windows WebAuthn unavailable'

class Native:
    @staticmethod
    def is_available(): return True
    def __init__(self, collector, allow_hmac_secret):
        assert allow_hmac_secret
        collector.verify_rp_id(yubikey_auth.RP_ID, yubikey_auth.ORIGIN)
    def get_assertion(self, options, event):
        event.set()  # python-fido2 uses this for successful completion, too.
        return 'native assertion'
    def make_credential(self, options, event):
        event.set()
        return 'native credential'

cancelled = threading.Event()
with patch.object(yubikey_auth, 'sys', SimpleNamespace(platform='win32')), patch.dict(sys.modules, {'fido2.client.windows': SimpleNamespace(WindowsClient=Native)}), patch.object(yubikey_auth, 'open_device', side_effect=AssertionError('Raw USB access on Windows')):
    with yubikey_auth.client_session(None, cancelled) as (client, interaction):
        assert client.make_credential({}, cancelled) == 'native credential'
        assert client.get_assertion({}, cancelled) == 'native assertion'
        assert not cancelled.is_set()
user_cancelled = threading.Event(); user_cancelled.set()
assert yubikey_auth.WindowsCancellation(user_cancelled).wait(.1)
with patch('key_ui.sys', SimpleNamespace(platform='win32')), patch('key_ui.QInputDialog.getText', side_effect=AssertionError('Duplicate PIN prompt')):
    assert request_key_pin(None, 'Unlock') == (None, True)

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_DATA_HOME'] = directory;os.environ['LOCALAPPDATA'] = directory
    root = Path(directory).resolve();local = root/'chosen.sqlite';share = root/'share';share.mkdir()
    vault = ManagedVault(local);vault.create('synthetic-master-password');vault.lock()
    window = ManagedWindow(root/'missing.sqlite')
    window.open_path(local)
    configure(window.vault, share, 10, automatic=False)
    with patch.object(managed_locations, 'sys', SimpleNamespace(platform='win32')):
        restarted = managed_locations.initial_vault()
        assert restarted == local
        assert managed_locations.initial_vault(root/'explicit.sqlite') == root/'explicit.sqlite'
    assert read_settings(ManagedVault(restarted))['folder'] == str(share)
    window.show();app.processEvents()
    fit_to_screen(window,1160,700,QRect(0,0,1024,600));app.processEvents()
    assert window.height() <= 536, window.size()
    assert window.width() <= 992, window.size()
    bottom = window.sync_status.mapTo(window, window.sync_status.rect().bottomRight()).y()
    assert bottom < window.height(), (bottom, window.height())
    window.auto_timer.stop();window.lock();window.hide()
print('PASS: native Windows key routing/cancellation, PIN prompt, last vault/NAS persistence and small-screen status visibility.')
