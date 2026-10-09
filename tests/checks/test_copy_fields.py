"""All field copy paths remain masked, clear on timeout/lock, preserve other clipboard data."""
import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit
from app import Window, EntryDialog, COPY_FIELDS
application=QApplication([])
with tempfile.TemporaryDirectory() as name:
    os.environ['XDG_DATA_HOME']=name
    window=Window(Path(name)/'dummy.sqlite')
    window.vault.create('dummy-test-password')
    record={'description':'Dummy mail','link':'https://example.com','user_name':'dummy@example.com',
            'password':'secret-without-reveal','notes':'Line one\nLine two — café'}
    window.vault.save(record); window.update_state(); window.refresh(); window.table.selectRow(0)
    for (field,label),action in zip(COPY_FIELDS,window.copy_menu.actions()):
        assert action.text()==label
        action.trigger()
        assert application.clipboard().text()==record[field]
        assert window.clipboard_timer.isActive() and window.clipboard_timer.interval()==30000
        assert window.password_display is None
        window.clipboard_timer.timeout.emit()
        assert application.clipboard().text()=='' and window.clipboard_value is None
    cell=window.table.cellWidget(0,4)
    button=next(b for b in cell.findChildren(QPushButton) if b.text()=='Copy')
    button.click()
    assert application.clipboard().text()==record['password']
    assert cell.findChild(QLineEdit).text()=='••••••••' and window.password_display is None
    application.clipboard().setText('another application copied this')
    window.clipboard_timer.timeout.emit()
    assert application.clipboard().text()=='another application copied this'
    dialog=EntryDialog(window,window.selected()); window.dialog=dialog
    for field,label in COPY_FIELDS:
        expected='unsaved '+label if field!='notes' else 'unsaved\nmultiline notes'
        if field=='notes': dialog.notes.setPlainText(expected)
        else: dialog.fields[field].setText(expected)
        dialog.findChild(QPushButton,'copy_'+field).click()
        assert application.clipboard().text()==expected
        assert dialog.fields['password'].echoMode()==QLineEdit.EchoMode.Password
    window.lock()
    assert application.clipboard().text()==''
    window.copy_field('password',record.get('id'))
    window.copy_text('must not copy while locked')
    assert application.clipboard().text()==''
    dialog.deleteLater(); window.dialog=None; window.close()
print('All field menu/buttons, masked row copy, unsaved values, 30-second timeout, ownership and lock guards passed.')
