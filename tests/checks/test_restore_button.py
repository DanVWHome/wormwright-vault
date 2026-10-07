"""Selected deleted records restore from both shared views."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as folder:
    w=ManagedWindow(Path(folder)/'vault.sqlite',True);w.auto_timer.stop()
    w.vault.create('DemoVault123!')
    ids=[w.vault.save({'description':name,'password':'dummy'}) for name in ['A','B']]
    w.vault.delete(ids[0]);w.show_deleted.setChecked(True);w.update_state();w.refresh();w.open_view(False)
    w.table.selectRow(0)
    assert w.delete_button.text()==w.companion.delete_button.text()=='Restore'
    w.delete_button.click();assert not w.vault.entries(True)[0]['deleted']
    assert w.delete_button.text()=='Delete'
    w.vault.delete(ids[1]);w.refresh();w.companion.table.selectRow(1)
    assert w.companion.delete_button.text()=='Restore'
    w.companion.delete_button.click();assert all(not r['deleted'] for r in w.vault.entries(True))
    w.lock();w.companion.hide();w.hide()
print('Restore button checks passed')
