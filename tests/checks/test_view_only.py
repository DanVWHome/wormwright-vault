"""View-only policy applies to existing entries, creation, Android and old clients."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault, verify
from vault import VaultError

def refused(action):
    try: action()
    except VaultError: return
    raise AssertionError('Write unexpectedly allowed')

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'vault.sqlite'
    manager=ManagedVault(path);manager.create('manager-test-password',managed=True)
    uid=manager.add_user('Reader','reader-test-password')
    new_uid=manager.add_user('New Reader','new-reader-password',view_only=True)
    new_reader=ManagedVault(path);new_reader.unlock('new-reader-password','New Reader')
    assert not new_reader.can_edit
    personal=new_reader.save({'description':'Private owned entry'})
    assert new_reader._record(personal)['groups']==[]
    assert new_reader.can_edit_entry(new_reader._record(personal))
    new_reader.lock()
    reader=ManagedVault(path);reader.unlock('reader-test-password','Reader')
    eid=manager.save({'description':'Shared by Manager','password':'visible-secret'})
    manager.set_view_only(uid,True)
    assert not reader.can_edit
    assert reader._record(eid)['password']=='visible-secret'
    own=reader.save({'description':'Owned private entry'})
    reader.save(dict(reader._record(own),password='owned-edit'))
    refused(lambda:reader.save(dict(reader._record(eid),password='changed')))
    refused(lambda:reader.delete(eid))
    refused(lambda:reader.set_view_only(uid,False))
    refused(lambda:manager.set_view_only(manager.uid,True))
    policy=verify(manager.meta['verify'].decode(),json.loads(manager.meta['authority']))
    assert policy['features']==['entry-ownership-v1','view-only-users-v1']
    # Legacy engines require exact equality and therefore reject this policy.
    assert policy != {'vault':manager.meta['vault_id'].decode(),'hash':manager._authority_hash()}
    # A signed update crafted by a reader must still fail validation.
    original=reader._record(eid)
    with reader.db:reader._write(dict(original,password='forged'))
    refused(lambda:manager.entries())
    with manager.db:manager._write(original)
    reader.lock();reader.unlock('reader-test-password','Reader')
    assert not reader.can_edit
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'android/app/src/main/python'))
    import mobile_bridge
    mobile_bridge.unlock(str(path),'Reader','reader-test-password',editable=True,sample=True)
    info=json.loads(mobile_bridge.editing_info())
    assert info['view_only'] and info['can_edit']
    assert json.loads(mobile_bridge.detail(eid))['password']=='visible-secret'
    refused(lambda:mobile_bridge.save_entry(json.dumps({'id':eid,'description':'Forbidden shared edit'})))
    refused(lambda:mobile_bridge.delete_entry(eid))
    mobile_bridge.lock()
    manager.set_view_only(uid,False)
    assert reader.can_edit
    reader.save(dict(reader._record(eid),password='editing-restored'))
    assert 'features' in json.loads(manager.meta['authority'])['data']
    reader.lock();manager.lock()
print('View-only checks passed.')
