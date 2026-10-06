from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os,sys,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication,QDialogButtonBox,QCheckBox
from app import Window,ImportPreview
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
 window=Window(folder+'/vault.sqlite');window.vault.create('test-master-passphrase')
 records=[dict(description='Demo Import',link='https://example.com',user_name='demo',password='dummy-secret!',notes='Preview only')]
 dialog=ImportPreview(window,records)
 buttons=dialog.findChild(QDialogButtonBox)
 assert not buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
 checkboxes=dialog.findChildren(QCheckBox)
 checkboxes[0].setChecked(True)
 assert dialog.table.item(0,3).text()=='dummy-secret!'
 checkboxes[1].setChecked(True)
 assert buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
 dialog.show();app.processEvents()
 window.dialog=dialog
 window.lock()
 assert dialog.table.rowCount()==0 and records==[]
 assert not window.vault.unlocked
print('PASS: preview masks, show for verification, explicit approval gate, auto-lock clears preview')
