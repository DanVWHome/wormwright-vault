import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from conflict_dialog import ConflictDialog
app = QApplication([])
class Dummy:
    def compare(self):
        a={'description':'Mail', 'password':'fictional-local', 'notes':'old'}
        b={'description':'Mail', 'password':'fictional-shared', 'notes':'new'}
        return [('mail',a,b),('extra',None,{'description':'Extra','password':'another-dummy'})]
d = ConflictDialog(None,Dummy())
assert not d.buttons.button(QDialogButtonBox.StandardButton.Apply).isEnabled()
assert 'fictional-local' not in d.local_text.toPlainText()
assert 'password' in d.table.item(0,2).text()
d.reveal.setChecked(True); assert 'fictional-local' in d.local_text.toPlainText()
d.choose_all('shared'); assert d.choices()==['shared','shared']
assert d.buttons.button(QDialogButtonBox.StandardButton.Apply).isEnabled()
d.clear_secrets(); assert not d.local_text.toPlainText() and not d.shared_text.toPlainText()
print('Masked comparison, explicit choices, reveal and clearing checks passed.')
