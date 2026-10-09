from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication, QMessageBox
from app import Window
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
    window=Window(Path(folder)/'vault.sqlite')
    window.vault.create('test-master-passphrase')
    record=dict(description='Original',link='',user_name='',password='dummy-secret',notes='')
    entry_id=window.vault.save(record)
    window.update_state()
    window.refresh()
    backup=str(Path(folder)/'backup.sqlite')
    with patch('app.QFileDialog.getSaveFileName',return_value=(backup,'')), patch('app.QMessageBox.information'):
        window.backup()
    assert Path(backup).exists()
    window.vault.save({**record,'id':entry_id,'description':'New edit'})
    with patch('app.QFileDialog.getOpenFileName',return_value=(backup,'')), patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes), patch('PySide6.QtWidgets.QInputDialog.getText',return_value=('test-master-passphrase',True)), patch('app.QMessageBox.information'):
        window.restore()
    assert window.vault.unlocked and window.table.rowCount()>0
    assert list(Path(folder).glob('*-before-restore-*.sqlite'))
    window.master.setText('test-master-passphrase')
    window.unlock()
    assert window.table.item(0,1).text()=='Original'
    window.lock()
print('PASS: backup and restore dialogs, safety snapshot, locked UI after restore, reopening restored entries')
