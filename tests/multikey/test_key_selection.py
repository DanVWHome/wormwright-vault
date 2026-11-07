import os, pathlib, sys, tempfile, threading, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
_runtime=tempfile.TemporaryDirectory(prefix='wormwright-keys-ui-')
os.environ['XDG_DATA_HOME']=_runtime.name
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from key_ui import choose_key
from app import Window
from managed_ui import ManagedWindow
APP=QApplication.instance() or QApplication([])
PW='Invented-Only-Password!'
class KeySelection(unittest.TestCase):
 def test_named_selection_and_cancel(self):
  keys=[{'id':'one','label':'Laptop'},{'id':'two','label':'Backup'}]
  with patch('PySide6.QtWidgets.QInputDialog.getItem',return_value=('Backup',True)):
   self.assertEqual(choose_key(None,keys),keys[1])
  with patch('PySide6.QtWidgets.QInputDialog.getItem',return_value=('',False)):
   self.assertIsNone(choose_key(None,keys))
 def test_desktop_enrollment_appends_without_replace_confirmation(self):
  with tempfile.TemporaryDirectory() as folder:
   w=Window(pathlib.Path(folder)/'vault.sqlite');w.auto_timer.stop();w.vault.create(PW)
   first=os.urandom(32);w.vault.enroll_yubikey(os.urandom(128),os.urandom(32),first,'Laptop')
   original=w.vault.yubikey_settings()
   with patch('app.QInputDialog.getText',side_effect=[(PW,True),('Phone',True)]),patch('app.request_key_pin',return_value=('DummyPinOnly',True)),patch('yubikey_auth.enroll',return_value=(os.urandom(128),os.urandom(32),os.urandom(32))),patch.object(w,'key_request',side_effect=lambda f:f(threading.Event())),patch('app.QMessageBox.information'),patch('app.QMessageBox.warning') as warning,patch('app.QMessageBox.question') as replace:
    w.enroll_key();warning.assert_not_called();replace.assert_not_called()
   self.assertEqual(w.vault.yubikey_enrollments()[0],original)
   self.assertEqual([k['label'] for k in w.vault.yubikey_enrollments()],['Laptop','Phone']);w.lock();w.close()
 def test_managed_unlock_uses_selected_backup(self):
  with tempfile.TemporaryDirectory() as folder:
   w=ManagedWindow(pathlib.Path(folder)/'vault.sqlite',False);w.auto_timer.stop();w.vault.create(PW)
   values={}
   for label in ['Laptop','Phone','Backup']:
    values[label]=os.urandom(32);w.vault.enroll_yubikey(os.urandom(128),os.urandom(32),values[label],label)
   w.vault.lock()
   def hardware(settings,pin,event):
    self.assertEqual(settings['label'],'Backup');return values['Backup']
   with patch('PySide6.QtWidgets.QInputDialog.getItem',return_value=('Backup',True)),patch('managed_ui.request_key_pin',return_value=('DummyPinOnly',True)),patch('yubikey_auth.unlock',side_effect=hardware),patch.object(w,'key_request',side_effect=lambda f:f(threading.Event())),patch.object(w,'auto_sync'),patch.object(w,'warning') as warning:
    w.unlock_key();warning.assert_not_called();self.assertTrue(w.vault.unlocked)
   w.lock();w.close()
if __name__=='__main__':unittest.main()
