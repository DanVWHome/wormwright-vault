"""Real desktop + companion engines; simulated shared directory, invented data.
Not evidence of Android UI, SMB transport or a physical NAS device test.
"""
import json
from pathlib import Path
import shutil
import sys
root=Path(sys.argv[1]);path=Path(sys.argv[2]);eid,deleted=sys.argv[3:5];expected=json.loads(sys.argv[5])
sys.path.insert(0,str(root/'src'))
from managed_vault import ManagedVault
import managed_sync
import sync
v=ManagedVault(path);v.unlock('Desktop-master-password!', 'Owner')
assert v.manager and v.personal
for k,value in expected.items():assert v._record(eid)[k]==value,(k,v._record(eid)[k],value)
assert v._record(deleted)['deleted']
# Provision a companion account with the desktop's existing administration.
groups=list(v.available_groups());v.add_user('PhoneDemo','Companion-synthetic-password!',groups)
shared=path.parent/'simulated-nas';shared.mkdir()
sync.configure(v,str(shared),10,automatic=False)
session=v.session();v.lock();managed_sync.synchronize(path,session)
remote=shared/'wormwright-vault.sqlite';assert remote.exists()
sys.path.insert(0,str(root/'android/app/src/main/python'))
import mobile_bridge as companion
import mobile_sync
phone=path.parent/'companion.sqlite';shutil.copyfile(remote,phone)
companion.validate_file(str(phone))
companion.unlock(str(phone),'PhoneDemo','Companion-synthetic-password!',True,False)
phone_session=companion._vault.session();result=path.parent/'pair.sqlite'
plan=mobile_sync.prepare(phone,remote,result,phone_session,'synthetic/share')
assert plan['ready'];companion.lock();mobile_sync.commit(phone,result,plan)
companion.unlock(str(phone),'PhoneDemo','Companion-synthetic-password!',True,False)
for k,value in expected.items():assert json.loads(companion.detail(eid))[k]==value
changed=dict(expected,id=eid,notes='Edited by invented companion account')
companion.save_entry(json.dumps(changed));phone_session=companion._vault.session();companion.lock()
plan=mobile_sync.prepare(phone,remote,result,phone_session,'synthetic/share');assert plan['ready'] and plan['upload']
shutil.copyfile(result,remote);mobile_sync.commit(phone,result,plan)
managed_sync.synchronize(path,session)
v=ManagedVault(path);v.unlock('Desktop-master-password!', 'Owner')
assert v._record(eid)['notes']=='Edited by invented companion account'
assert v._record(deleted)['deleted'];v.restore_entry(deleted);assert not v._record(deleted)['deleted'];v.lock()
print('PASS desktop management → simulated shared directory → companion pairing/edit/upload → desktop download; fields and tombstones preserved')
