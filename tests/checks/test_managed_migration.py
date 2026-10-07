import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from vault import Vault
from managed_vault import ManagedVault,convert_personal
with tempfile.TemporaryDirectory() as root:
 root=Path(root);old=Vault(root/'old.sqlite');old.create('old-dummy-password')
 old.save({'description':'Migrated','password':'csv-secret','notes':'Dummy only'})
 old.change_password('old-dummy-password','short');original=old.path.read_bytes();old.lock()
 target=root/'converted.sqlite';convert_personal(root/'old.sqlite',target,'short','Manager')
 assert (root/'old.sqlite').read_bytes()==original
 new=ManagedVault(target);new.unlock('short');assert new.personal and new.manager
 assert new.entries()[0]['password']=='csv-secret'
 assert {r[0] for r in new.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}>={'users','groups','exclusions','entries'}
 response=b'x'*32;new.enroll_yubikey(b'dummy-credential',b's'*32,response);settings=new.yubikey_settings();new.lock();new.unlock_yubikey(settings,response);assert new.manager
 generic=next(iter(new.available_groups()));uid=new.add_user('Alice','alice-password',[generic]);new.lock();new.unlock('alice-password','Alice')
 new.enroll_yubikey(b'alice-credential',b'a'*32,b'y'*32);alice_settings=new.yubikey_settings();new.lock()
 try:new.unlock_yubikey(alice_settings,response)
 except Exception:pass
 else:raise AssertionError('Wrong hardware response unlocked account')
 new.unlock_yubikey(alice_settings,b'y'*32);assert new.uid==uid and not new.manager;new.lock()
 # A failed conversion cannot remove an existing destination.
 existing=root/'existing.sqlite';existing.write_bytes(b'leave this file alone')
 try:convert_personal(root/'old.sqlite',existing,'short')
 except Exception:pass
 else:raise AssertionError('Overwrote an existing destination')
 assert existing.read_bytes()==b'leave this file alone'
print('New schema, preserved source, shorter migrated fallback, per-account hardware and destination safety checks passed.')
