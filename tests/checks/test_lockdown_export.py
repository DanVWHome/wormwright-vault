import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault,AccountUnavailable
from managed_sync import synchronize,state
from sync import configure
from vault import VaultError
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);share=root/'share';share.mkdir()
    manager=ManagedVault(root/'manager.sqlite');manager.create('ManagerDemo123!')
    group=next(iter(manager.available_groups()))
    alice=manager.add_user('Alice','AliceDemo123!',[group]);bob=manager.add_user('Bob','BobDemo123!',[group])
    manager.save({'description':'Shared dummy','password':'dummy'})
    recipient=ManagedVault(root/'recipient.sqlite');manager.export_database(recipient.path)
    recipient.unlock('AliceDemo123!','Alice');assert len(recipient.entries())==1
    try:recipient.export_database(root/'forbidden.sqlite')
    except VaultError:pass
    else:raise AssertionError('Ordinary account exported whole database')
    original=recipient.path.read_bytes()
    try:manager.export_database(recipient.path)
    except FileExistsError:pass
    else:raise AssertionError('Export overwrote existing vault')
    assert recipient.path.read_bytes()==original
    configure(manager,share,2);configure(recipient,share,2)
    synchronize(manager.path,manager.session());synchronize(recipient.path,recipient.session())
    manager.reset_password(alice,'NewAliceDemo123!');synchronize(manager.path,manager.session())
    synchronize(recipient.path,recipient.session());recipient.resume(recipient.session());assert recipient.unlocked
    recipient.lock()
    try:recipient.unlock('AliceDemo123!','Alice')
    except VaultError:pass
    else:raise AssertionError('Old password accepted after sync')
    recipient.unlock('NewAliceDemo123!','Alice');saved=recipient.session()
    assert manager.emergency_lockdown()==2
    assert manager.unlocked and len(manager.entries())==1
    assert all(u['identity']['disabled'] for uid,u in manager.administration()['users'].items() if uid!=manager.uid)
    synchronize(manager.path,manager.session());synchronize(recipient.path,saved)
    try:recipient.resume(saved)
    except AccountUnavailable:pass
    else:raise AssertionError('Lockdown did not revoke unlocked session')
    assert not recipient.unlocked and state(recipient.path)==state(manager.path)
    for name,password in [('Alice','NewAliceDemo123!'),('Bob','BobDemo123!')]:
        try:recipient.unlock(password,name)
        except AccountUnavailable:pass
        else:raise AssertionError('Disabled login accepted')
    manager.set_disabled(alice,False);manager.export_database(root/'recovery.sqlite')
    recovery=ManagedVault(root/'recovery.sqlite');recovery.unlock('NewAliceDemo123!','Alice');assert len(recovery.entries())==1
    recovery.lock();manager.lock()
print('Password reset sync, encrypted export permissions/overwrite protection, lockdown session revocation and individual recovery passed')
