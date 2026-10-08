"""Synthetic hardware reauthentication, staged replacement and real header ordering."""
import sys,tempfile
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow
from managed_vault import ManagedVault
from vault import VaultError
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as d:
    root=Path(d);w=ManagedWindow(root/'vault.sqlite',True);w.auto_timer.stop();w.vault.create('DemoVault123!')
    for name,user in [('C','alice'),('A','zoe'),('B','bob')]:w.vault.save({'description':name,'user_name':user,'password':{'C':'Zulu9','A':'Alpha1','B':'Middle5'}[name]})
    w.update_state();w.refresh();w.open_view(False);w.table.selectRow(1);selected=w.selected()['id']
    w.table.horizontalHeader().sectionClicked.emit(0)
    assert [r['description'] for r in w.records]==['C','B','A'] and w.selected()['id']==selected
    w.companion.table.horizontalHeader().sectionClicked.emit(2)
    assert [r['user_name'] for r in w.records]==['alice','bob','zoe']
    assert w.companion.table.item(0,0).text()=='C'
    w.companion.table.selectRow(2);assert w.selected()['description']=='A'
    # Masked password headers must not leak ordering or change the viewport.
    before=([r['id'] for r in w.records],w.sort_column,w.sort_descending,w.selected()['id'],w.table.verticalScrollBar().value())
    for table in (w.table,w.companion.table):
        for _ in range(3):table.horizontalHeader().sectionClicked.emit(3)
        assert ([r['id'] for r in w.records],w.sort_column,w.sort_descending,w.selected()['id'],w.table.verticalScrollBar().value())==before
        assert 'disabled' in table.horizontalHeaderItem(3).toolTip()
    # Qt moves its indicator before sectionClicked: exercise actual mouse clicks.
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt,QPoint
    w.show();w.companion.show();app.processEvents()
    for table in (w.table,w.companion.table):
        header=table.horizontalHeader()
        for _ in range(2):
            QTest.mouseClick(header.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(header.sectionViewportPosition(3)+header.sectionSize(3)//2,header.height()//2))
            assert header.sortIndicatorSection()==w.sort_column
            assert header.sortIndicatorOrder()==(Qt.SortOrder.DescendingOrder if w.sort_descending else Qt.SortOrder.AscendingOrder)
    # Defensive refresh never uses a secret as its sort key, even with stale state.
    w.sort_column=3;w.sort_descending=False;w.refresh()
    assert [r['description'] for r in w.records]==['A','B','C']
    response=b'h'*32;w.vault.enroll_yubikey(b'dummy-credential',b's'*32,response)
    # Simulate user choosing enrolled hardware; no USB or real credentials used.
    with patch('managed_ui.QMessageBox') as box,patch('managed_ui.QInputDialog.getText',return_value=('dummy-pin',True)),patch('yubikey_auth.unlock',return_value=response):
        dialog=box.return_value;key=object();fallback=object();dialog.addButton.side_effect=[key,fallback,object()];dialog.clickedButton.return_value=key
        with patch.object(w,'key_request',side_effect=lambda operation:operation(None)):
            authentication=w.reauthenticate()
    assert authentication['yubikey_response']==response
    w.vault.change_password(None,'NewDemo123!',**authentication)
    target=root/'export.sqlite';w.vault.export_database(target);old=target.read_bytes()
    w.vault.save({'description':'new','password':'dummy'})
    with patch.object(w.vault,'backup',side_effect=OSError('simulated export failure')):
        try:w.vault.export_database(target,overwrite=True)
        except OSError:pass
        else:raise AssertionError('Export failure suppressed')
    assert target.read_bytes()==old
    w.vault.export_database(target,overwrite=True)
    exported=ManagedVault(target);exported.unlock('NewDemo123!');assert len(exported.entries())==4;exported.lock()
    try:w.vault.export_database(w.vault.path,overwrite=True)
    except VaultError:pass
    else:raise AssertionError('Overwrote open vault')
    # The UI offers an explicit overwrite decision; declining preserves the file.
    from PySide6.QtWidgets import QMessageBox
    before=target.read_bytes()
    with patch.object(w,'reauthenticate',return_value={'password':'NewDemo123!'}),patch('managed_ui.QFileDialog.getSaveFileName',return_value=(str(target),'')),patch('managed_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.No) as question:
        w.export_database();assert question.called
    assert target.read_bytes()==before
    # Failed hardware verification returns no authentication proof.
    with patch('managed_ui.QMessageBox') as box,patch('managed_ui.QInputDialog.getText',return_value=('dummy-pin',True)),patch('yubikey_auth.unlock',return_value=b'wrong'*6+b'xx'),patch.object(w,'warning'):
        dialog=box.return_value;key=object();dialog.addButton.side_effect=[key,object(),object()];dialog.clickedButton.return_value=key
        with patch.object(w,'key_request',side_effect=lambda operation:operation(None)):
            assert w.reauthenticate() is None
    w.lock();w.companion.hide();w.hide()
print('Hardware reauthentication, selected-record sorting, staged overwrite and failure preservation checks passed')
