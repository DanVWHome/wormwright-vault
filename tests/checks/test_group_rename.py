"""Rename preserves group identity, entries, exclusions and default selection."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from vault import VaultError

def refused(operation):
 try:operation()
 except VaultError:return
 raise AssertionError('Unauthorized or invalid rename succeeded')
with tempfile.TemporaryDirectory() as directory:
 a=ManagedVault(Path(directory)/'test.sqlite');a.create('manager-test-password',managed=True)
 gid=a.default_group_id();parents=a.add_group('Parents');uid=a.add_user('Macie','macie-test-password',[gid],view_only=True)
 eid=a.save({'description':'Shared demo','password':'fake-secret','groups':[gid]});a.set_excluded(eid,uid,True)
 before=a.administration();record=a._record(eid);fields=('description','password','groups','creator','owner','deleted')
 a.rename_group(gid,'Family');after=a.administration()
 assert after['groups'][gid]['name']=='Family'
 assert after['groups'][gid]['members']==before['groups'][gid]['members']
 assert after['exclusions']==before['exclusions']
 assert all(a._record(eid)[key]==record[key] for key in fields)
 assert a.default_group_id()==gid
 added=a.add_user('Dan','dan-test-password');assert added in a.administration()['groups'][gid]['members']
 new=a.save({'description':'Default still Family'});assert a._record(new)['groups']==[gid]
 child=ManagedVault(a.path);child.unlock('macie-test-password','Macie');assert eid not in {row['id'] for row in child.entries()};assert new in {row['id'] for row in child.entries()}
 refused(lambda:child.rename_group(gid,'Escalation'))
 refused(lambda:a.rename_group(gid,' parents '));refused(lambda:a.rename_group(gid,' '));refused(lambda:a.rename_group('missing','Name'))
 child.lock();a.lock()
print('Group rename preserves identity, membership, entries, exclusions and defaults; Manager enforcement passed.')
