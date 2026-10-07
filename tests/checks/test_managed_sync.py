import sys,tempfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from managed_sync import synchronize,state
from sync import configure,SyncConflict
with tempfile.TemporaryDirectory() as root:
    root=Path(root);share=root/'share';share.mkdir()
    a=ManagedVault(root/'a.sqlite');a.create('manager-dummy-password')
    generic=next(iter(a.available_groups()));alice=a.add_user('Alice','alice-dummy-password',[generic])
    first=a.save({'description':'First','password':'one'});second=a.save({'description':'Second','password':'two'})
    b=ManagedVault(root/'b.sqlite');a.backup(b.path);b.unlock('alice-dummy-password','Alice')
    configure(a,share,2);configure(b,share,2)
    synchronize(a.path,a.session());synchronize(b.path,b.session())
    r=a._record(first);r['notes']='manager edit';a.save(r)
    r=b._record(second);r['notes']='alice edit';b.save(r)
    synchronize(b.path,b.session());result=synchronize(a.path,a.session());assert 'Merged' in result
    a.resume(a.session());assert a._record(second)['notes']=='alice edit'
    b.resume(b.session());synchronize(b.path,b.session());b.resume(b.session());assert b._record(first)['notes']=='manager edit'
    b.delete(first);synchronize(b.path,b.session());synchronize(a.path,a.session());a.resume(a.session())
    assert first not in [r['id'] for r in a.entries()] and a._record(first)['deleted']
    a.restore_entry(first);synchronize(a.path,a.session())
    synchronize(b.path,b.session());b.resume(b.session());assert b._record(first)['deleted'] is False
    # Locked sync uses ciphertext and signed policy only.
    r=a._record(second);r['notes']='locked transfer';a.save(r);synchronize(a.path,a.session())
    session=b.session();b.lock();synchronize(b.path);assert not b.unlocked;b.resume(session);assert b._record(second)['notes']=='locked transfer'
    # Concurrent authority changes cannot be silently merged.
    a.add_group('Manager change');b.change_password('alice-dummy-password','new-alice-password')
    synchronize(a.path,a.session())
    try:synchronize(b.path,b.session())
    except SyncConflict:pass
    else:raise AssertionError('Administrative conflict overwritten')
    a.lock();b.lock()
print('Independent user edits, soft delete/restore, locked sync and administrative conflict checks passed.')
# Explicit administrative reconciliation authenticates both originals and
# re-encrypts chosen entries under the Manager-selected policy.
with tempfile.TemporaryDirectory() as root:
 from managed_sync import reconcile
 root=Path(root);share=root/'share';share.mkdir()
 a=ManagedVault(root/'a.sqlite');a.create('manager-dummy-password')
 generic=next(iter(a.available_groups()));uid=a.add_user('Alice','alice-password',[generic]);eid=a.save({'description':'Shared','password':'original'})
 b=ManagedVault(root/'b.sqlite');a.backup(b.path);b.unlock('manager-dummy-password','Manager')
 configure(a,share,2);configure(b,share,2);synchronize(a.path,a.session());synchronize(b.path,b.session())
 a.set_excluded(eid,uid,True)
 record=b._record(eid);record['password']='edited';b.save(record);synchronize(b.path,b.session())
 expected=[state(a.path),state(share/'wormwright-vault.sqlite')]
 result=reconcile(a.path,a.session(),'local',{eid:'shared'},expected)
 assert 'Reconciled' in result;a.resume(a.session());assert a._record(eid)['password']=='edited'
 user=ManagedVault(a.path);user.unlock('alice-password','Alice');assert not user.entries();user.lock()
 b.resume(b.session());synchronize(b.path,b.session());b.resume(b.session());assert b._record(eid)['password']=='edited'
 user=ManagedVault(root/'user.sqlite');b.backup(user.path);user.unlock('alice-password','Alice')
 configure(user,share,2);synchronize(user.path,user.session());saved_session=user.session()
 a.set_disabled(uid,True);synchronize(a.path,a.session())
 synchronize(user.path,saved_session)
 try:user.resume(saved_session)
 except Exception:pass
 else:raise AssertionError('Disabled session remained active')
 assert not user.unlocked and state(user.path)==state(a.path)
 assert state(share/'wormwright-vault.sqlite')==state(a.path)
 a.lock();b.lock()
print('Manager reconciliation retained entry edits and individual exclusion policy.')
