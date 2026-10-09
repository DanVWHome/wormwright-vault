"""Named format-2 vaults retain identity, policy and unrelated vaults."""
from pathlib import Path
import sys,tempfile,sqlite3,json,os
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from vault import VaultError
from PySide6.QtWidgets import QApplication,QLineEdit,QDialogButtonBox,QListWidget
from PySide6.QtCore import QTimer,Qt
from managed_ui import ManagedWindow
from unittest.mock import patch
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as d:
    base=Path(d).resolve();os.environ['XDG_DATA_HOME']=str(base);os.environ['LOCALAPPDATA']=str(base);v=ManagedVault(base/'named.sqlite');v.create('Invented-Name-Test-Password!',vault_name=' Family ')
    assert v.display_name=='Family';authority=v.meta['authority'];identity=v.meta['vault_id'];v.set_display_name('Personal')
    assert v.display_name=='Personal' and v.meta['authority']==authority and v.meta['vault_id']==identity
    backup=base/'backup.sqlite';v.backup(backup);v.lock();assert v.display_name=='Personal';b=ManagedVault(backup);b.unlock('Invented-Name-Test-Password!');assert b.display_name=='Personal';b.lock()
    for name in ['', '  ', 'x'*81,'line\nline',None]:
        p=base/'invalid.sqlite'
        try:ManagedVault(p).create('Invented-Name-Test-Password!',vault_name=name if name is not None else '') ;raise AssertionError('Invalid name accepted')
        except VaultError:assert not p.exists()
    v.unlock('Invented-Name-Test-Password!');user=v.add_user('Viewer','Invented-Viewer-Password!',list(v.available_groups()));v.lock();v.unlock('Invented-Viewer-Password!','Viewer')
    assert v.display_name=='Personal'
    try:v.set_display_name('Unauthorized');raise AssertionError('Ordinary account renamed shared vault')
    except VaultError:pass
    v.lock()
    with sqlite3.connect(backup) as db:
        name=json.loads(db.execute("SELECT value FROM metadata WHERE name='display_name'").fetchone()[0]);name['data']['name']='Tampered'
        db.execute("UPDATE metadata SET value=? WHERE name='display_name'",(json.dumps(name).encode(),))
    db.close() # SQLite's transaction context commits but does not close the handle.
    try:ManagedVault(backup).unlock('Invented-Name-Test-Password!');raise AssertionError('Tampered name accepted')
    except VaultError:pass
    # Existing unnamed files are still readable; no inferred name is silently saved.
    legacy=ManagedVault(base/'earlier.sqlite');legacy.create('Invented-Earlier-Password!');assert legacy.display_name=='';legacy.lock()
    window=ManagedWindow(base/'new.sqlite');window.auto_timer.stop()
    def create_dialog():
        prompt=QApplication.activeModalWidget();fields=prompt.findChildren(QLineEdit);buttons=prompt.findChild(QDialogButtonBox)
        fields[1].setText('InventedManager');fields[2].setText('Invented-New-Vault-Password!');fields[3].setText('Invented-New-Vault-Password!')
        buttons.button(QDialogButtonBox.StandardButton.Save).click();assert prompt.isVisible() and not (base/'new.sqlite').exists()
        fields[0].setText('New named vault');buttons.button(QDialogButtonBox.StandardButton.Save).click()
    QTimer.singleShot(0,create_dialog);assert window.create_account(base/'new.sqlite');assert window.vault.display_name=='New named vault';window.update_state()
    def inspect_list():
        prompt=QApplication.activeModalWidget();listing=prompt.findChild(QListWidget);assert listing.count()==2
        assert listing.item(0).text().startswith('New named vault (current)\n');assert listing.item(0).data(Qt.ItemDataRole.UserRole)==str(base/'new.sqlite')
        assert listing.item(1).text().startswith('Unnamed vault\n');prompt.reject()
    with patch.object(window.history,'read',return_value=[str(base/'new.sqlite'),str(base/'earlier.sqlite')]):QTimer.singleShot(0,inspect_list);window.recent()
    window.close()
print('PASS required creation name, signed name integrity, stable identity/policy, backup retention, locked labels, Manager-only rename, existing unnamed compatibility, named desktop vault list')
