"""Clicking Use Password accepts immediate keyboard input in Vault and Manager."""
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from managed_vault import ManagedVault
from managed_ui import ManagedWindow
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base=Path(directory);os.environ['XDG_DATA_HOME']=directory;os.environ['LOCALAPPDATA']=directory
    path=base/'invented.sqlite';vault=ManagedVault(path);vault.create('Invented-Focus-Password!',vault_name='Focus test');vault.lock()
    for manager in (False,True):
        window=ManagedWindow(path,manager_app=manager);window.auto_timer.stop();window.show();window.activateWindow();app.processEvents()
        with patch.object(window.vault,'yubikey_settings',return_value={'invented':True}):
            window.update_state();assert not window.master.isVisible() and window.fallback.isVisible()
            QTest.mouseClick(window.fallback,Qt.MouseButton.LeftButton);app.processEvents()
            assert window.master.isVisible() and app.focusWidget() is window.master
            QTest.keyClicks(app.focusWidget(),'InventedTyping');assert window.master.text()=='InventedTyping'
        window.master.clear();window.close();window.deleteLater();app.processEvents()
print('PASS immediate password focus and typing in Vault and Manager')
