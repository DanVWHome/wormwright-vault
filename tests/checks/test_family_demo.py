"""The second demo is separate, has expected permissions, and cannot overwrite."""
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
from help_window import HelpWindow
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as directory:
 os.environ['XDG_DATA_HOME']=directory
 w=ManagedWindow(Path(directory)/'uncreated.sqlite',True);target=Path(directory)/'family.sqlite'
 with patch('managed_ui.QFileDialog.getSaveFileName',return_value=(str(target),'')),patch('managed_ui.QMessageBox.information'):
  w.load_family_demo();assert target.exists() and not w.vault.unlocked
  original=target.read_bytes()
  with patch.object(w,'warning') as warn:w.load_family_demo();assert warn.called and target.read_bytes()==original
 for name,password,visible,editable in [('FamilyManager','Demo-Manager-2026!',23,23),('Dan','Demo-Dan-2026!',16,16),('Nikki','Demo-Nikki-2026!',16,16),('Macie','Demo-Macie-2026!',11,5),('Onyx','Demo-Onyx-2026!',1,0)]:
  w.vault.unlock(password,name);w.update_state();w.refresh();rows=w.vault.entries()
  assert len(rows)==visible and sum(w.vault.can_edit_entry(row) for row in rows)==editable
  assert w.management_menu.menuAction().isVisible()==(name=='FamilyManager')
  if name=='Onyx':assert rows[0]['description'].startswith('Netflix')
  w.lock()
 h=HelpWindow(w);h.search.setText('FamilyManager');assert h.tree.topLevelItemCount()>0
 h.search.setText('Manage menu missing');assert h.tree.topLevelItemCount()>0
 assert 'Opening the Vault Manager application alone does not grant administrative rights' in h.text.toPlainText()
 w.close_ready=True;w.close()
print('Second demo copy safety, five account views, Manager menu visibility and searchable family help passed.')
