from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os, sys, tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from app import Window
app = QApplication([])
with tempfile.TemporaryDirectory() as folder:
    window = Window(folder + '/vault.sqlite')
    window.vault.create('test-master-passphrase')
    for description, password in [('A', 'first-demo-secret'), ('B', 'second-demo-secret')]:
        window.vault.save(dict(description=description, password=password, link='', user_name='', notes=''))
    window.refresh()
    cells = [window.table.cellWidget(row, 4) for row in range(2)]
    labels = [cell.findChild(QLineEdit) for cell in cells]
    buttons = [cell.findChild(QPushButton) for cell in cells]
    assert window.table.item(0, 4).text() == ''
    buttons[0].click()
    assert labels[0].text() == 'first-demo-secret' and labels[1].text() == '••••••••'
    assert buttons[0].text() == 'Hide'
    buttons[1].click()
    assert labels[1].text() == 'second-demo-secret'
    buttons[0].click()
    assert labels[0].text() == '••••••••'
    window.search.setText('B')
    assert window.table.cellWidget(0, 4).findChild(QLineEdit).text() == '••••••••'
    window.table.cellWidget(0, 4).findChild(QPushButton).click()
    window.lock()
    assert window.table.rowCount() == 0 and not window.vault.unlocked
print('PASS: independent row reveal/hide, correct passwords, search re-masking, lock removes rows')
