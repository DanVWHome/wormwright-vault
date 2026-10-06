import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QPushButton, QMessageBox
from PySide6.QtCore import QTimer
from app import Window
from vault import Vault

application = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_DATA_HOME'] = directory
    root = Path(directory)
    first = root / 'first.sqlite'; second = root / 'second.sqlite'
    window = Window(first); window.vault.create('fictional-master-password'); window.remember_vault()
    vault = Vault(second); vault.create('fictional-master-password'); vault.lock()
    window.vault_history.remember(second)
    missing = root / 'missing.sqlite'; window.vault_history.remember(missing)
    def use_recent():
        dialog = next(d for d in window.findChildren(QDialog) if d.windowTitle() == 'Recent Vaults')
        locations = dialog.findChild(QListWidget)
        open_button = next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Open selected')
        forget = next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Forget selected')
        locations.setCurrentRow(0)
        with patch.object(QMessageBox, 'warning') as warning:
            open_button.click()
            assert warning.called and window.vault.unlocked
        forget.click()
        assert not missing.exists() and second.exists()
        locations.setCurrentRow(0)
        open_button.click()
    QTimer.singleShot(0, use_recent)
    window.recent_vaults()
    assert window.vault.path == second and not window.vault.unlocked
    assert first.exists() and second.exists()
    window.master.setText('fictional-master-password'); window.unlock()
    assert window.vault_history.read()[0] == str(second)
    window.lock()
print('PASS: unavailable locations retained, forget only history, recent open locks, successful unlock remembers')
