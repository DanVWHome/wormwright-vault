from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys,os,tempfile
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication
from app import Window
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
 window=Window(folder+'/vault.sqlite')
 window.vault.create('test-master-passphrase')
 response=os.urandom(32)
 window.vault.enroll_yubikey(b'dummy-credential',os.urandom(32),response)
 window.show();window.lock();app.processEvents()
 assert window.key_unlock_button.isVisible() and not window.master.isVisible()
 window.show_fallback();assert window.master.isVisible()
 window.lock()
 with patch('app.QInputDialog.getText',return_value=('dummy-pin',True)),patch('yubikey_auth.unlock',return_value=response):
  window.unlock_key()
 assert window.vault.unlocked and not window.key_unlock_button.isVisible()
 window.lock()
 with patch('app.QInputDialog.getText',return_value=('dummy-pin',True)),patch('yubikey_auth.unlock',side_effect=ValueError('Dummy hardware failure')),patch('app.QMessageBox.warning') as warning:
  window.unlock_key()
 assert not window.vault.unlocked and warning.called
 window.show_fallback();window.master.setText('test-master-passphrase');window.unlock();assert window.vault.unlocked
 window.lock()
print('PASS: YubiKey primary UI, fallback visibility, asynchronous unlock, hardware-error fallback, password still works')
