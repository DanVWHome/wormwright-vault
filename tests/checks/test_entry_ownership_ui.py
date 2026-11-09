"""Entry selection enforces shared read-only versus owned edits in both views."""
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtCore import QTimer
from managed_ui import ManagedWindow
from managed_vault import ManagedVault
app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
 os.environ['XDG_DATA_HOME']=directory;path=Path(directory)/'fixture.sqlite'
 w=ManagedWindow(path,True);w.vault.create('manager-test-password',managed=True)
 uid=w.vault.add_user('Macie','macie-test-password',view_only=True)
 other=w.vault.add_user('Onyx','onyx-test-password',view_only=True)
 shared=w.vault.save({'description':'Family Netflix','password':'fake-shared'})
 child=ManagedVault(path);child.unlock('macie-test-password','Macie')
 own=child.save({'description':'Macie Google','password':'fake-owned'});child.lock()
 w.lock();w.vault.unlock('macie-test-password','Macie');w.update_state();w.refresh();w.open_view(False)
 def select(eid):
  w.table.selectRow(next(i for i,r in enumerate(w.records) if r['id']==eid));app.processEvents()
 def enabled(text):return next(b.isEnabled() for b in w.controls if b.text()==text)
 select(shared);assert not enabled('Edit') and not enabled('Delete') and enabled('Add')
 assert not next(b for b in w.companion.buttons if b.text()=='Edit').isEnabled()
 select(own);assert enabled('Edit') and enabled('Delete')
 assert next(b for b in w.companion.buttons if b.text()=='Edit').isEnabled()
 def accept_edit():
  assert w.dialog is not None;w.dialog.notes.setPlainText('Owner edited this in the desktop UI.');w.dialog.accept()
 QTimer.singleShot(0,accept_edit);w.edit()
 assert w.vault._record(own)['notes']=='Owner edited this in the desktop UI.'
 w.lock();w.vault.unlock('manager-test-password','Manager');w.update_state();w.refresh();select(own)
 label='Onyx ('+other[:8]+')'
 with patch('managed_ui.QInputDialog.getItem',return_value=(label,True)):
  w.change_owner()
 assert w.vault.owner_id(w.vault._record(own))==other
 w.lock();w.close_ready=True;w.close()
print('Shared/owned selection, both views, real owner-edit dialog and Manager ownership-transfer UI passed.')
