"""Dummy-data UI: conditional username, soft deletion, search and clipboard isolation."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
application=QApplication([])
with tempfile.TemporaryDirectory() as name:
 os.environ['XDG_DATA_HOME']=name
 w=ManagedWindow(Path(name)/'dummy.sqlite',True);w.vault.create('manager-dummy-password')
 gid=next(iter(w.vault.available_groups()));family=w.vault.add_group('Family')
 uid=w.vault.add_user('Alice','alice-dummy-password',[family])
 private=w.vault.save({'description':'Manager private','password':'private','groups':[gid]})
 shared=w.vault.save({'description':'Family mail','password':'mail-secret','groups':[family]})
 w.vault.delete(shared);w.update_state();w.refresh();assert w.table.rowCount()==1
 w.show_deleted.setChecked(True);assert w.table.rowCount()==2
 assert any(w.table.item(i,5).text()=='Deleted' for i in range(w.table.rowCount()))
 w.vault.restore_entry(shared);w.lock();w.vault.unlock('alice-dummy-password','Alice');w.update_state();w.refresh()
 assert w.table.rowCount()==1 and w.records[0]['id']==shared
 assert w.manager_row.isHidden();w.search.setText('Manager private');assert w.table.rowCount()==0
 w.search.clear();w.copy_field('password');assert application.clipboard().text()=='mail-secret';w.lock();assert not application.clipboard().text()
 w.update_state();assert not w.username.isHidden()
 w.close_ready=True;w.close()
print('Managed UI login, filtering, deleted checkbox, search isolation and clipboard checks passed.')
