from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os,sys,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app import Window
from vault import VaultError
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
 window=Window(folder+'/vault.sqlite');window.vault.create('test-master-passphrase')
 QTimer.singleShot(30,window.lock)
 try:
  window.key_request(lambda cancelled: (cancelled.wait(1),b'ignored')[1])
  raise AssertionError('cancelled result returned')
 except VaultError:
  assert not window.vault.unlocked and window.key_task is None
print('PASS: auto-lock cancels background hardware task and discards its result')
