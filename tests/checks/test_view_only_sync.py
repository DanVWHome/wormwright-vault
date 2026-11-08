"""Downloaded restrictions replace stale policy; competing edits need review."""
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from managed_sync import synchronize
from sync import configure, SyncConflict
from vault import VaultError
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);share=root/'share';share.mkdir()
    manager=ManagedVault(root/'manager.sqlite');manager.create('manager-test-password',managed=True)
    uid=manager.add_user('Reader','reader-test-password')
    eid=manager.save({'description':'Shared entry','password':'visible-secret'})
    reader=ManagedVault(root/'reader.sqlite');manager.backup(reader.path)
    reader.unlock('reader-test-password','Reader')
    configure(manager,share,2);configure(reader,share,2)
    synchronize(manager.path,manager.session());synchronize(reader.path,reader.session())
    # Keep a paired pre-restriction device with an unsynced edit.
    stale=ManagedVault(root/'stale.sqlite');shutil.copyfile(reader.path,stale.path)
    stale.unlock('reader-test-password','Reader');configure(stale,share,2)
    synchronize(stale.path,stale.session())
    stale.save(dict(stale._record(eid),password='offline-edit'))
    manager.set_view_only(uid,True);synchronize(manager.path,manager.session())
    session=reader.session();reader.lock();synchronize(reader.path);reader.resume(session)
    assert not reader.can_edit and reader._record(eid)['password']=='visible-secret'
    try:reader.save(dict(reader._record(eid),password='forbidden'))
    except VaultError:pass
    else:raise AssertionError('Downloaded permission did not block editing')
    try:synchronize(stale.path,stale.session())
    except SyncConflict:pass
    else:raise AssertionError('Stale offline edit silently replaced new permissions')
    shared=ManagedVault(share/'wormwright-vault.sqlite');shared.unlock('reader-test-password','Reader')
    assert not shared.can_edit and shared._record(eid)['password']=='visible-secret'
    shared.lock();stale.lock();reader.lock();manager.lock()
print('Locked sync applies view-only permissions; competing stale writes need Manager review.')
