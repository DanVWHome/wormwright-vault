from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys, tempfile, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(SOURCE))
from PySide6.QtWidgets import QApplication, QLineEdit
from app import Window, EntryDialog
app = QApplication([])
with tempfile.TemporaryDirectory() as folder:
    window = Window(folder + '/demo.sqlite')
    window.vault.create('test-master-passphrase')
    for description, username, password in [('Demo Mail','demo@example.com','Demo-only-password!'),('Demo Router','admin','Another-demo-password!'),('Demo Account','demo','Demo-only-password!')]:
        window.vault.save(dict(description=description, link='https://example.com', user_name=username, password=password, notes='Dummy entry'))
    window.update_state()
    window.refresh()
    window.show()
    app.processEvents()
    assert window.table.rowCount() == 3
    assert window.table.item(0, 5).text() == 'Used in 2 entries'
    window.search.setText('router')
    assert window.table.rowCount() == 1
    window.table.selectRow(0)
    window.copy()
    assert app.clipboard().text() == 'Another-demo-password!'
    app.clipboard().setText('unrelated clipboard')
    window.clear_clipboard()
    assert app.clipboard().text() == 'unrelated clipboard'
    dialog = EntryDialog(window, window.selected())
    show = next(button for button in dialog.findChildren(__import__('PySide6.QtWidgets', fromlist=['QPushButton']).QPushButton) if button.text() == 'Show')
    show.click()
    assert dialog.fields['password'].echoMode() == QLineEdit.EchoMode.Normal
    show.click()
    assert dialog.fields['password'].echoMode() == QLineEdit.EchoMode.Password
    dialog.deleteLater()
    window.search.clear()
    window.table.selectRow(0)
    window.copy()
    window.lock()
    assert window.table.rowCount() == 0
    assert not window.records and not window.vault.unlocked
    assert app.clipboard().text() == ''
    assert all(not button.isEnabled() for button in window.controls)
    window.close()
print('PASS: Qt rendering, table, duplicates, search, selection, reveal/hide, clipboard ownership, lock clearing')
