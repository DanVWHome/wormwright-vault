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
    display = window.password_display
    assert display.isVisible()
    assert display.password_text.toPlainText() == 'first-demo-secret'
    assert display.password_text.font().pointSize() == 32
    assert labels[0].text() == labels[1].text() == '••••••••'
    buttons[1].click()
    assert display.password_text.toPlainText() == '' and not display.isVisible()
    assert window.password_display.password_text.toPlainText() == 'second-demo-secret'
    display = window.password_display
    display.close()
    assert display.password_text.toPlainText() == ''
    buttons[0].click()
    display = window.password_display
    window.search.setText('B')
    assert display.password_text.toPlainText() == '' and window.password_display is None
    window.table.cellWidget(0, 4).findChild(QPushButton).click()
    display = window.password_display
    window.lock()
    assert display.password_text.toPlainText() == '' and not display.isVisible()
    assert window.table.rowCount() == 0 and not window.vault.unlocked
print('PASS: large password window, masked table, switching/closing/search/lock clear plaintext')
