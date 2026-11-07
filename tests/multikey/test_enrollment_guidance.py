"""Real Qt worker/UI handoff: explain each operation before native prompts."""
import contextlib
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication,QWidget,QMessageBox
from app import Window
from vault import VaultError
import yubikey_auth as auth
from key_ui import ENROLLMENT_STEPS
APP=QApplication.instance() or QApplication([])
class Host(QWidget):
    key_request=Window.key_request
class GuidanceTests(unittest.TestCase):
    def test_both_steps_acknowledged_in_order_before_hardware(self):
        host=Host();events=[]
        def explain(parent,title,text,*buttons):
            self.assertEqual(threading.current_thread(),threading.main_thread())
            self.assertLess(parent.sizeHint().width(), 800)
            events.append(title);return QMessageBox.StandardButton.Ok
        def operation(cancelled,stage):
            stage(1);events.append('create');stage(2);events.append('verify');return 'complete'
        with patch('app.QMessageBox.information',side_effect=explain):
            self.assertEqual(host.key_request(operation,enrollment=True),'complete')
        self.assertEqual(events,[ENROLLMENT_STEPS[1][0],'create',ENROLLMENT_STEPS[2][0],'verify'])
        host.close()
    def test_cancel_second_step_stops_before_verification(self):
        host=Host();events=[]
        def operation(cancelled,stage):
            stage(1);events.append('create');stage(2);events.append('verify')
        with patch('app.QMessageBox.information',side_effect=[QMessageBox.StandardButton.Ok,QMessageBox.StandardButton.Cancel]):
            with self.assertRaises(VaultError):host.key_request(operation,enrollment=True)
        self.assertEqual(events,['create']);self.assertIsNone(host.key_task);host.close()
    def test_cancel_first_step_stops_before_creation(self):
        host=Host();events=[]
        def operation(cancelled,stage):stage(1);events.append('create')
        with patch('app.QMessageBox.information',return_value=QMessageBox.StandardButton.Cancel):
            with self.assertRaises(VaultError):host.key_request(operation,enrollment=True)
        self.assertEqual(events,[]);host.close()
    def test_enrollment_announces_creation_then_secret_verification(self):
        client=Mock();interaction=SimpleNamespace(requested=True,pin=None);service=Mock();events=[]
        service.register_begin.return_value=({'publicKey':{}},'state')
        credential=b'invented-credential'
        registration=SimpleNamespace(client_extension_results={'hmacCreateSecret':True})
        client.make_credential.side_effect=lambda *a,**kw:events.append('create') or registration
        service.register_complete.return_value=SimpleNamespace(credential_data=credential)
        with patch.object(auth,'client_session',return_value=contextlib.nullcontext((client,interaction))),patch.object(auth,'server',return_value=service),patch.object(auth,'authenticate',side_effect=lambda *a:events.append('verify') or b'x'*32):
            result=auth.enroll(None,threading.Event(),lambda step:events.append(step))
        self.assertEqual(events,[1,'create',2,'verify']);self.assertEqual(result[0],credential)
if __name__=='__main__':unittest.main()
