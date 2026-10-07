"""The secondary view shares one controller and clears on lock or lost privilege."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
app=QApplication([])
with tempfile.TemporaryDirectory() as d:
 os.environ['XDG_DATA_HOME']=d
 for manager in (False,True):
  w=ManagedWindow(Path(d)/str(manager),manager);w.vault.create('dummy-master-password','Dan')
  group=w.vault.add_group('Family');w.vault.add_user('Alice','dummy',[group])
  w.vault.save({'description':'Shared','password':'secret','groups':[group]});w.update_state();w.refresh();w.open_view(not manager)
  c=w.companion;assert c.controller is w and c.table.rowCount()==1
  c.search.setText('Missing');assert w.table.rowCount()==0 and c.table.rowCount()==0
  c.search.clear();w.vault.save({'description':'Second','password':'secret','groups':[group]});w.refresh();assert c.table.rowCount()==2
  w.copy_text('secret');w.lock();assert not app.clipboard().text() and c.table.rowCount()==0 and not c.buttons[0].isEnabled()
  w.vault.unlock('dummy','Alice');w.update_state();w.refresh()
  if c.manager:assert c.table.rowCount()==0 and not any(a.isEnabled() for a in c.management) and not c.buttons[0].isEnabled()
  w.close_ready=True;w.close()
print('Companion state, search, edits, clipboard/lock and Manager privilege checks passed.')
