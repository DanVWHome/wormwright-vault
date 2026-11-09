"""Owners edit their own entries; policy-signed transfers cannot be forged."""
import json,sys,tempfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault,pack
from vault import VaultError
from managed_sync import synchronize
from sync import configure,SyncConflict

def refused(operation):
 try:operation()
 except VaultError:return
 raise AssertionError('Unauthorized operation succeeded')
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);path=root/'vault.sqlite'
 manager=ManagedVault(path);manager.create('manager-test-password',managed=True)
 gid=next(iter(manager.available_groups()))
 macie=manager.add_user('Macie','macie-test-password',[gid],view_only=True)
 onyx=manager.add_user('Onyx','onyx-test-password',[gid],view_only=True)
 netflix=manager.save({'description':'Netflix shared','password':'fake-netflix'})
 amazon=manager.save({'description':'Amazon shared','password':'fake-amazon'})
 manager.set_excluded(amazon,onyx,True)
 m=ManagedVault(path);m.unlock('macie-test-password','Macie')
 o=ManagedVault(path);o.unlock('onyx-test-password','Onyx')
 assert m.can_create and not m.can_edit and not m.can_edit_entry(m._record(netflix))
 refused(lambda:m.save(dict(m._record(netflix),password='forbidden')))
 refused(lambda:m.delete(netflix))
 original=manager._record(netflix)
 forged=dict(original,creator=macie)
 m._assignment(forged)
 with m.db:m._write(forged)
 refused(lambda:manager._record(netflix))
 with manager.db:manager._write(original)
 google=m.save({'description':'Macie Google (fictional)','password':'fake-google'})
 record=m._record(google);assert record['owner']==macie and record['groups']==[]
 assert m.can_edit_entry(record)
 m.save(dict(record,password='changed-owned'))
 refused(lambda:o._record(google));refused(lambda:o._record(amazon))
 assert {r['id'] for r in o.entries()}=={netflix}
 assert manager._record(google)['password']=='changed-owned'
 refused(lambda:m.set_owner(google,onyx))
 refused(lambda:m.save(dict(m._record(google),owner=onyx)))
 # Preserve an old signed payload to test a former owner's attempt to reclaim it.
 old=path.read_bytes();old_record=m._record(google)
 manager.set_owner(google,onyx)
 refused(lambda:m._record(google))
 record=o._record(google);assert record['owner']==onyx and o.can_edit_entry(record)
 o.save(dict(record,password='new-owner-edit'))
 assert manager._record(google)['password']=='new-owner-edit'
 # A forged entry owner field cannot change the Manager-signed override.
 stale=ManagedVault(root/'stale.sqlite');stale.path.write_bytes(old);stale.unlock('macie-test-password','Macie')
 # Rebuild an envelope under the CURRENT policy using the former owner's keys.
 # Its author must be rejected even though they originally created the entry.
 m._refresh_cap()
 with m.db:m._write(dict(old_record,password='forged',owner=macie))
 refused(lambda:manager._record(google))
 with manager.db:manager._write(record)
 assert o._record(google)['owner']==onyx
 manager.set_disabled(macie,True);refused(lambda:manager.set_owner(google,macie))
 manager.set_disabled(macie,False)
 # Assigning ownership grants access even if a previous exclusion exists.
 manager.set_excluded(netflix,macie,True);manager.set_owner(netflix,macie)
 assert m._record(netflix)['owner']==macie and m.can_edit_entry(m._record(netflix))
 # Android must allow own edits but refuse shared edits, with NAS/pairing gates retained.
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'android/app/src/main/python'))
 import mobile_bridge
 mobile_bridge.unlock(str(path),'Onyx','onyx-test-password',editable=True,sample=True)
 assert json.loads(mobile_bridge.detail(google))['view_only'] is False
 assert json.loads(mobile_bridge.detail(netflix))['view_only'] is True
 mobile_bridge.save_entry(json.dumps({'id':google,'description':'Owned on Android','password':'mobile-owned'}))
 refused(lambda:mobile_bridge.save_entry(json.dumps({'id':netflix,'description':'Forbidden shared edit'})))
 mobile_bridge.lock()
 stale.lock();m.lock();o.lock();manager.lock()
print('Owned edits, private creation, Manager transfers, former-owner forgery rejection and Android entry permissions passed.')
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);share=root/'share';share.mkdir()
 a=ManagedVault(root/'manager.sqlite');a.create('manager-test-password',managed=True)
 uid=a.add_user('Macie','macie-test-password',view_only=True);other=a.add_user('Onyx','onyx-test-password',view_only=True)
 m=ManagedVault(root/'macie.sqlite');a.backup(m.path);m.unlock('macie-test-password','Macie')
 configure(a,share,2);configure(m,share,2)
 synchronize(a.path,a.session());synchronize(m.path,m.session())
 eid=m.save({'description':'Private owned email','password':'original'})
 synchronize(m.path,m.session());synchronize(a.path,a.session());a.resume(a.session())
 # Pair a second owner device; its competing stale edit must require review.
 stale=ManagedVault(root/'stale.sqlite');shutil.copyfile(m.path,stale.path);stale.unlock('macie-test-password','Macie');configure(stale,share,2);synchronize(stale.path,stale.session())
 stale.save(dict(stale._record(eid),password='stale-owner-edit'))
 a.set_owner(eid,other);synchronize(a.path,a.session())
 session=m.session();m.lock();synchronize(m.path);m.resume(session);refused(lambda:m._record(eid))
 try:synchronize(stale.path,stale.session())
 except SyncConflict:pass
 else:raise AssertionError('Former-owner offline edit bypassed ownership transfer')
 target=ManagedVault(m.path);target.unlock('onyx-test-password','Onyx');assert target.can_edit_entry(target._record(eid));target.lock()
 stale.lock();m.lock();a.lock()
print('Ownership transfer sync removes former-owner access; stale edits need Manager review.')
# Model the exact legacy authority shape and UUID entries before migration.
with tempfile.TemporaryDirectory() as directory:
 from managed_vault import sign
 path=Path(directory)/'legacy.sqlite';a=ManagedVault(path);a.create('manager-test-password',managed=True)
 uid=a.add_user('Macie','macie-test-password')
 document=pack(sign(a._signer(),{'vault':a.meta['vault_id'].decode(),'hash':a._authority_hash()}))
 with a.db:a.db.execute("UPDATE metadata SET value=? WHERE name='authority'",(document,))
 a._refresh_cap();assert not a.ownership_enabled
 m=ManagedVault(path);m.unlock('macie-test-password','Macie')
 legacy=m.save({'description':'Legacy owned entry'});assert ':' not in legacy
 shared=a.save({'description':'Legacy shared entry'});assert ':' not in shared
 a.enable_ownership();a.set_view_only(uid,True)
 assert a.cap['owners'][legacy]==uid and a.cap['owners'][shared]==a.uid
 assert m.can_edit_entry(m._record(legacy)) and not m.can_edit_entry(m._record(shared))
 original=a._record(shared);forged=dict(original,creator=uid);m._assignment(forged)
 with m.db:m._write(forged)
 refused(lambda:a._record(shared))
 with a.db:a._write(original)
 m.lock();a.lock()
print('Legacy UUID entries gain signed owner bindings; creator substitution is rejected after migration.')
# Manager reconciliation must retain private entries and selected ownership.
with tempfile.TemporaryDirectory() as directory:
 from managed_sync import reconcile,state
 root=Path(directory);share=root/'share';share.mkdir()
 a=ManagedVault(root/'a.sqlite');a.create('manager-test-password',managed=True)
 uid=a.add_user('Macie','macie-test-password',view_only=True);other=a.add_user('Onyx','onyx-test-password',view_only=True)
 child=ManagedVault(a.path);child.unlock('macie-test-password','Macie');eid=child.save({'description':'Private email'});child.lock()
 b=ManagedVault(root/'b.sqlite');a.backup(b.path);b.unlock('manager-test-password','Manager')
 configure(a,share,2);configure(b,share,2);synchronize(a.path,a.session());synchronize(b.path,b.session())
 a.set_owner(eid,other);b.save(dict(b._record(eid),notes='Manager kept this edit'));synchronize(b.path,b.session())
 expected=[state(a.path),state(share/'wormwright-vault.sqlite')]
 reconcile(a.path,a.session(),'local',{eid:'shared'},expected);a.resume(a.session())
 record=a._record(eid);assert record['groups']==[] and record['owner']==other and record['notes']=='Manager kept this edit'
 child=ManagedVault(a.path);child.unlock('macie-test-password','Macie');refused(lambda:child._record(eid));child.lock()
 a.lock();b.lock()
print('Manager reconciliation retains private entries, content edits and selected ownership policy.')
