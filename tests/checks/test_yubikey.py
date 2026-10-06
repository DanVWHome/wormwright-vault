from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys,tempfile,os
from pathlib import Path
sys.path.insert(0, str(SOURCE))
from vault import Vault,VaultError
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);v=Vault(root/'vault.sqlite');old='test-master-passphrase';new='new-fallback-password'
 v.create(old)
 v.save(dict(description='Key test',link='',user_name='demo',password='dummy-secret',notes=''))
 response=os.urandom(32);salt=os.urandom(32);credential=b'dummy-credential'
 try:v.verify_password('wrong');raise AssertionError('accepted wrong password')
 except VaultError:pass
 safety=v.enroll_yubikey(credential,salt,response)
 settings=v.yubikey_settings()
 assert settings['credential']==credential and settings['salt']==salt
 assert response not in v.path.read_bytes() and v.data_key not in v.path.read_bytes()
 before=Vault(safety);before.unlock(old);assert before.yubikey_settings() is None;before.lock()
 v.lock();v.unlock_yubikey(settings,response)
 assert v.entries()[0]['password']=='dummy-secret'
 v.lock()
 try:v.unlock_yubikey(settings,os.urandom(32));raise AssertionError('wrong key accepted')
 except VaultError:assert not v.unlocked
 v.unlock(old)
 safety=v.change_password(old,new)
 assert v.yubikey_settings()==settings
 v.lock()
 try:v.unlock(old);raise AssertionError('old password accepted')
 except VaultError:pass
 v.unlock(new);assert len(v.entries())==1;v.lock()
 v.unlock_yubikey(settings,response);assert len(v.entries())==1
 snapshot=root/'backup.sqlite';v.backup(snapshot);v.lock()
 backup=Vault(snapshot);backup.unlock_yubikey(backup.yubikey_settings(),response);assert len(backup.entries())==1;backup.lock()
 original=Vault(safety);original.unlock(old);assert len(original.entries())==1;original.lock()
print('PASS: hardware key wrapping, wrong-key rejection, password fallback, password change, enrollment/password safety backups, encrypted backup retains YubiKey access')
