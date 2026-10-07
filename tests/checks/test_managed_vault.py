"""Synthetic accounts: cryptographic isolation, policy, signatures and soft deletion."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault, pack
from vault import VaultError


def refused(operation):
    try: operation()
    except Exception: return
    raise AssertionError('Unauthorized operation succeeded')

with tempfile.TemporaryDirectory() as root:
    path=Path(root)/'dummy.sqlite'
    manager=ManagedVault(path);manager.create('manager-dummy-password')
    generic=next(iter(manager.available_groups()))
    family=manager.add_group('Family')
    alice=manager.add_user('Alice','alice-dummy-password',[family])
    bob=manager.add_user('Bob','bob-dummy-password',[family])
    eid=manager.save({'description':'Family mail','password':'hidden-family-secret','groups':[family]})
    private=manager.save({'description':'Manager private','password':'private-secret','groups':[generic]})
    a=ManagedVault(path);a.unlock('alice-dummy-password','Alice')
    assert [r['id'] for r in a.entries()]==[eid]
    refused(lambda:a._record(private));refused(lambda:a.administration())
    refused(lambda:a.add_group('Escalation'))
    r=a.entries()[0];r['password']='changed-by-alice';a.save(r)
    r['groups']=[generic];refused(lambda:a.save(r))
    made=a.save({'description':'Created by Alice','password':'alice-secret','groups':[family]})
    refused(lambda:a.save({'description':'Wrong group','groups':[generic]}))
    a.delete(eid);assert eid not in [r['id'] for r in a.entries()]
    refused(lambda:a.entries(True));refused(lambda:a.restore_entry(eid));refused(lambda:a.purge(eid))
    manager.resume(manager.session());assert manager._record(eid)['deleted']
    manager.restore_entry(eid)
    manager.set_excluded(eid,alice,True)
    a.resume(a.session());assert eid not in [r['id'] for r in a.entries()]
    refused(lambda:a._record(eid))
    b=ManagedVault(path);b.unlock('bob-dummy-password','Bob')
    assert b._record(eid)['password']=='changed-by-alice'
    manager.set_memberships(alice,[])
    a.resume(a.session());assert [r['id'] for r in a.entries()]==[made]
    manager.set_excluded(made,alice,True)
    a.resume(a.session());assert not a.entries()
    manager.set_disabled(alice,True);refused(lambda:a.resume(a.session()))
    manager.reset_password(bob,'new-password')
    b.lock();refused(lambda:b.unlock('bob-dummy-password','Bob'));b.unlock('new-password','Bob')
    manager.delete(made);manager.purge(made)
    assert manager.db.execute('SELECT 1 FROM entries WHERE id=?',(made,)).fetchone() is None
    # Manager group membership is permanent; renaming retains credentials and role.
    assert all(manager.uid in g['members'] for g in manager.administration()['groups'].values())
    refused(lambda:manager.set_memberships(manager.uid,[]))
    manager.rename_manager('Dan')
    refused(lambda:manager.rename_manager('Bob'))
    manager.lock();manager.unlock('manager-dummy-password','Dan')
    assert manager.manager
    # Altering encrypted policy is rejected, even before ordinary-user unlock.
    with manager.db:
        manager.db.execute('UPDATE groups SET payload=? WHERE id=?',(b'forged',family))
    refused(lambda:b.unlock('new-password','Bob'))
    manager.lock();a.lock();b.lock()
    raw=path.read_bytes()
    assert b'private-secret' not in raw and b'Family mail' not in raw and b'Alice' not in raw
print('Managed access, creation/editing, exclusions, signatures, soft deletion, restore and purge checks passed.')
