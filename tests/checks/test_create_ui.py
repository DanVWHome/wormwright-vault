"""New vault creation must ask for both values, even with an empty main field."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QDialogButtonBox, QLabel
from PySide6.QtCore import QTimer
from app import Window

application = QApplication([])
with tempfile.TemporaryDirectory() as folder:
    window = Window(str(Path(folder) / 'new.sqlite'))
    def fill_dialog():
        dialog = next(d for d in window.findChildren(QDialog) if d.windowTitle() == 'Create encrypted vault')
        password = dialog.findChild(QLineEdit, 'new_master_password')
        confirm = dialog.findChild(QLineEdit, 'confirm_master_password')
        buttons = dialog.findChild(QDialogButtonBox)
        password.setText('disposable-test-password')
        confirm.setText('different-password')
        buttons.accepted.emit()
        assert dialog.result() != QDialog.DialogCode.Accepted
        assert any('do not match' in label.text() for label in dialog.findChildren(QLabel))
        assert not window.vault.path.exists()
        password.setText('short'); confirm.setText('short')
        buttons.accepted.emit()
        assert any('12 characters' in label.text() for label in dialog.findChildren(QLabel))
        assert not window.vault.path.exists()
        password.setText('disposable-test-password'); confirm.setText(password.text())
        buttons.accepted.emit()
    QTimer.singleShot(0, fill_dialog)
    assert window.master.text() == ''
    window.unlock()
    assert window.vault.unlocked and window.vault.path.exists()
    window.lock()
    window.vault.unlock('disposable-test-password')
    window.lock()
    other = Window(str(Path(folder) / 'cancelled.sqlite'))
    def cancel_dialog():
        dialog = next(d for d in other.findChildren(QDialog) if d.windowTitle() == 'Create encrypted vault')
        dialog.reject()
    QTimer.singleShot(0, cancel_dialog)
    other.unlock()
    assert not other.vault.path.exists()
print('PASS: two-field creation, mismatch and length validation, empty main field, cancellation and reopen')
