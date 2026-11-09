"""Exercise the Manager permission dialog and view-only desktop controls."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QListWidget, QPushButton
from managed_ui import ManagedWindow
app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_DATA_HOME']=directory
    w=ManagedWindow(Path(directory)/'synthetic.sqlite',True)
    w.vault.create('manager-test-password',managed=True)
    uid=w.vault.add_user('Reader','reader-test-password')
    eid=w.vault.save({'description':'Shared password','password':'copyable-secret'})
    w.update_state();w.refresh()
    errors=[]
    def set_permission():
        try:
            dialog=app.activeModalWidget()
            details=next(label for label in dialog.findChildren(QLabel) if label.text()=='Select a user to see their groups.')
            assert details.minimumHeight()>=details.fontMetrics().lineSpacing()*4
            users=dialog.findChild(QListWidget,'management_users')
            for index in range(users.count()):
                if users.item(index).data(256)==uid:users.setCurrentRow(index);break
            def accept_permission():
                try:
                    child=app.activeModalWidget()
                    checkbox=child.findChild(QCheckBox,'user_view_only')
                    assert checkbox is not None
                    checkbox.setChecked(True);child.accept()
                except Exception as error:errors.append(error);app.activeModalWidget().reject()
            QTimer.singleShot(0,accept_permission)
            next(b for b in dialog.findChildren(QPushButton) if b.text()=='Permissions…').click()
            assert 'View only' in ' '.join(x.text() for x in dialog.findChildren(QLabel))
            dialog.accept()
        except Exception as error:
            errors.append(error)
            if app.activeModalWidget():app.activeModalWidget().reject()
    QTimer.singleShot(0,set_permission);w.manage()
    assert not errors,errors
    w.lock();w.vault.unlock('reader-test-password','Reader');w.update_state();w.refresh();w.table.selectRow(0)
    assert w.records[0]['id']==eid
    for button in w.controls:
        if button.text() in ('Edit','Delete'):assert not button.isEnabled(),button.text()
        if button.text() in ('Add','Clone'):assert button.isEnabled(),button.text()
    w.open_view(False)
    assert all(not b.isEnabled() for b in w.companion.buttons if b.text() in ('Edit','Delete'))
    with patch('app.EntryDialog',side_effect=AssertionError('Editor opened for view-only user')):
        w.edit()
    w.copy_field('password');assert app.clipboard().text()=='copyable-secret'
    w.lock();assert not app.clipboard().text()
    w.close_ready=True;w.close()
print('Manager permission dialog, view-only controls, secondary view and copy/lock passed.')
