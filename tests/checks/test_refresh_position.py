"""Refresh preserves actual selection, viewport and unchanged row widgets."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as folder:
    w=ManagedWindow(Path(folder)/'vault.sqlite',True);w.auto_timer.stop();w.vault.create('DemoVault123!')
    for n in range(65):w.vault.save({'description':f'Entry {n:03}','password':'dummy'})
    w.update_state();w.refresh();w.show();app.processEvents();w.open_view(False);app.processEvents()
    w.companion.table.selectRow(45);app.processEvents()
    chosen=w.selected()['id'];main_scroll=w.table.verticalScrollBar().value();other_scroll=w.companion.table.verticalScrollBar().value()
    main_widget=w.table.cellWidget(45,3);other_widget=w.companion.table.cellWidget(45,3)
    w.refresh();w.update_state()
    assert w.table.cellWidget(45,3) is main_widget and w.companion.table.cellWidget(45,3) is other_widget
    assert w.selected()['id']==chosen
    w.show_deleted.setChecked(True);w.table.selectRow(45);chosen=w.selected()['id']
    w.vault.delete(chosen);w.refresh();assert w.selected()['id']==chosen and w.delete_button.text()=='Restore'
    w.vault.restore_entry(chosen);w.refresh();assert w.selected()['id']==chosen and w.delete_button.text()=='Delete'
    assert w.table.verticalScrollBar().value()==main_scroll
    assert w.companion.table.verticalScrollBar().value()==other_scroll
    w.show_deleted.setChecked(False);w.vault.delete(chosen);w.refresh();assert w.table.currentRow()==45
    assert w.selected()['id']!=chosen
    w.lock();w.companion.hide();w.hide()
print('Selection, nearest-row fallback, scroll and no-change widget checks passed')
