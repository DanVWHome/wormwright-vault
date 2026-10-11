"""Synthetic mounted-share discovery and folder chooser behavior."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
from pathlib import Path
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QFileDialog
import shared_folder_picker as picker
app = QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / 'runtime'
    home = Path(directory) / 'home'
    mount = runtime / 'gvfs/smb-share:server=192.168.1.144,share=Family%20Vault'
    mount.mkdir(parents=True)
    (runtime / 'gvfs/sftp:host=example').mkdir()
    assert picker.mounted_shares(runtime, home) == [('Family Vault on 192.168.1.144', mount)]
    assert picker.mounted_shares(Path(directory) / 'missing', home) == []
    selected = str(mount / 'Wormwright')
    observed = []
    def pick():
        dialog = app.activeModalWidget()
        items = dialog.findChild(QListWidget, 'connected_nas_shares')
        observed.append(items.item(0).text())
        # Double click a friendly share name, with no paths entered by the user.
        items.itemDoubleClicked.emit(items.item(0))
    with patch.object(picker, 'mounted_shares', return_value=[('Family Vault on 192.168.1.144', mount)]), patch.object(QFileDialog, 'getExistingDirectory', return_value=selected) as choose:
        QTimer.singleShot(0, pick)
        assert picker.choose_shared_folder(None) == selected
        assert observed == ['Family Vault on 192.168.1.144']
        assert choose.call_args.args[2] == str(mount)
        assert choose.call_args.args[3] & QFileDialog.Option.DontUseNativeDialog
    with patch.object(picker, 'mounted_shares', return_value=[]), patch.object(QFileDialog, 'getExistingDirectory') as choose:
        QTimer.singleShot(0, lambda: app.activeModalWidget().reject())
        assert picker.choose_shared_folder(None) == ''
        choose.assert_not_called()
    with patch.object(picker.sys, 'platform', 'win32'), patch.object(QFileDialog, 'getExistingDirectory', return_value='C:/NAS'):
        assert picker.choose_shared_folder(None, 'C:/NAS') == 'C:/NAS'
print('PASS: friendly NAS discovery, local mount navigation, cancellation and Windows fallback')
with tempfile.TemporaryDirectory() as directory:
    mount = Path(directory) / 'smb-share:server=nas,share=vaults'
    mount.mkdir()
    vault = str(mount / 'test.sqlite')
    def select_nas():
        dialog = app.activeModalWidget()
        assert dialog.windowTitle() == 'Open vault'
        items = dialog.findChild(QListWidget, 'connected_nas_shares')
        items.itemDoubleClicked.emit(items.item(0))
    with patch.object(picker, 'mounted_shares', return_value=[('vaults on nas', mount)]), patch.object(QFileDialog, 'getOpenFileName', return_value=(vault, '')) as choose:
        QTimer.singleShot(0, select_nas)
        assert picker.choose_vault_file(None) == vault
        assert choose.call_args.args[2] == str(mount)
        assert choose.call_args.kwargs['options'] & QFileDialog.Option.DontUseNativeDialog
    with patch.object(picker, 'mounted_shares', return_value=[]), patch.object(QFileDialog, 'getOpenFileName') as choose:
        QTimer.singleShot(0, lambda: app.activeModalWidget().reject())
        assert picker.choose_vault_file(None) == ''
        choose.assert_not_called()
    def browse_local():
        from PySide6.QtWidgets import QPushButton
        dialog = app.activeModalWidget()
        next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Browse other folders…').click()
    with patch.object(picker, 'mounted_shares', return_value=[]), patch.object(QFileDialog, 'getOpenFileName', return_value=(vault, '')) as choose:
        QTimer.singleShot(0, browse_local)
        assert picker.choose_vault_file(None, directory) == vault
        assert choose.call_args.args[2] == directory
    with patch.object(picker.sys, 'platform', 'win32'), patch.object(QFileDialog, 'getOpenFileName', return_value=('C:/test.sqlite', '')):
        assert picker.choose_vault_file(None) == 'C:/test.sqlite'
print('PASS: Open Vault NAS selection, cancellation, local browse and Windows fallback')
