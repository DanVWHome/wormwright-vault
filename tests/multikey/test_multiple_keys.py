import base64, json, os, pathlib, sqlite3, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from vault import Vault,VaultError
from managed_vault import ManagedVault
from hardware_keys import decode,encode
PW='Invented-Only-Password!'

class MultipleKeys(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'vault.sqlite'
 def tearDown(self):self.tmp.cleanup()
 def run_engine(self,kind):
  v=kind(self.path);v.create(PW);v.save({'description':'Synthetic fixture','password':'InventedSecret'})
  material=[]
  for name in ['Laptop','Phone','Backup','Spare']:
   c,s,r=os.urandom(128),os.urandom(32),os.urandom(32);v.enroll_yubikey(c,s,r,name)
   material.append((v.yubikey_enrollments()[-1],r))
  self.assertEqual([k['label'] for k in v.yubikey_enrollments()],['Laptop','Phone','Backup','Spare'])
  before=v.path.read_bytes()
  with self.assertRaises(VaultError):v.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),'Fifth')
  self.assertEqual(before,v.path.read_bytes())
  for setting,response in material:
   v.lock();v.unlock_yubikey(setting,response);self.assertEqual(v.entries()[0]['password'],'InventedSecret')
  v.lock();v.unlock(PW)
  v.rename_yubikey(material[1][0]['id'],'Phone NFC')
  old=material[1][0];new=v.yubikey_enrollments()[1];self.assertEqual(old['id'],new['id'])
  self.assertEqual(old['credential'],new['credential'])
  v.lock()
  with self.assertRaises(VaultError):v.unlock_yubikey(old,material[1][1])
  v.unlock_yubikey(new,material[1][1]);v.remove_yubikey(material[0][0]['id']);v.lock()
  with self.assertRaises(VaultError):v.unlock_yubikey(*material[0])
  v.unlock_yubikey(*material[2]);self.assertEqual(len(v.yubikey_enrollments()),3)
  v.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),'Replacement laptop')
  v.verify_yubikey(*material[2]);v.change_password(PW,'Changed-Only-Password!')
  snapshot=self.path.with_name('backup.sqlite');v.backup(snapshot);v.lock()
  b=kind(snapshot);b.unlock_yubikey(*material[2]);self.assertEqual(len(b.yubikey_enrollments()),4);b.lock()
  v.unlock('Changed-Only-Password!');v.lock()
 def test_legacy_engine_four_keys(self):self.run_engine(Vault)
 def test_format2_four_keys(self):self.run_engine(ManagedVault)
 def test_original_single_enrollment_is_preserved_on_add(self):
  for kind in [Vault,ManagedVault]:
   path=self.path.with_name(kind.__name__+'.sqlite');v=kind(path);v.create(PW)
   c,s,r=os.urandom(128),os.urandom(32),os.urandom(32);v.enroll_yubikey(c,s,r,'First')
   one=dict(v.yubikey_enrollments()[0]);one.pop('id');one.pop('label');one.pop('user',None)
   for f in ['credential','salt','wrapped_key']:one[f]=base64.b64encode(one[f]).decode()
   with v.db:
    if kind==Vault:v.db.execute("UPDATE metadata SET value=? WHERE name='yubikey'",(json.dumps(one).encode(),))
    else:v.db.execute('UPDATE users SET hardware=? WHERE id=?',(json.dumps(one).encode(),v.uid))
   v.lock();before=path.read_bytes();original=v.yubikey_settings();self.assertEqual(path.read_bytes(),before)
   v.unlock_yubikey(original,r);v.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),'Phone')
   self.assertEqual(v.yubikey_enrollments()[0],original)
   v.lock();v.unlock_yubikey(original,r);v.lock()
 def test_duplicate_name_or_credential_does_not_replace(self):
  v=ManagedVault(self.path);v.create(PW);c,s,r=os.urandom(128),os.urandom(32),os.urandom(32);v.enroll_yubikey(c,s,r,'Laptop');old=v.yubikey_enrollments()
  with self.assertRaises(VaultError):v.enroll_yubikey(c,s,r,'Same credential')
  with self.assertRaises(VaultError):v.enroll_yubikey(os.urandom(128),s,r,'laptop')
  self.assertEqual(v.yubikey_enrollments(),old);v.lock()
 def test_account_isolation_and_revocation(self):
  v=ManagedVault(self.path);v.create(PW,username='Manager',managed=True);uid=v.add_user('Member',PW);v.lock();v.unlock(PW,'Member')
  keys=[]
  for name in ['Laptop','Phone','Backup','Spare']:
   r=os.urandom(32);v.enroll_yubikey(os.urandom(128),os.urandom(32),r,name);keys.append((v.yubikey_enrollments()[-1],r))
  v.lock();v.unlock(PW,'Manager');self.assertEqual(v.yubikey_enrollments(),[])
  v.set_disabled(uid,True);v.lock()
  for key,r in keys:
   with self.assertRaises(VaultError):v.unlock_yubikey(key,r)
   self.assertFalse(v.unlocked)
 def test_concurrent_additions_cannot_overwrite_or_exceed_limit(self):
  from concurrent.futures import ThreadPoolExecutor
  import threading
  v=ManagedVault(self.path);v.create(PW)
  for i in range(3):v.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),'Existing '+str(i))
  v.lock();barrier=threading.Barrier(2)
  def add(label):
   item=ManagedVault(self.path);item.unlock(PW);barrier.wait()
   try:item.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),label);return True
   except VaultError:return False
   finally:item.lock()
  with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(add,['Phone','Backup']))
  self.assertEqual(sorted(result),[False,True]);self.assertEqual(len(ManagedVault(self.path).yubikey_enrollments()),4)
 def test_sync_keeps_all_keys_and_rejects_competing_key_changes(self):
  from managed_sync import synchronize
  from sync import configure,SyncConflict
  share=self.path.parent/'share';share.mkdir();a=ManagedVault(self.path);a.create(PW)
  b=ManagedVault(self.path.with_name('phone.sqlite'));a.backup(b.path);b.unlock(PW)
  configure(a,share,2);configure(b,share,2);synchronize(a.path,a.session());synchronize(b.path,b.session())
  for name in ['Laptop','Phone','Backup','Spare']:a.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32),name)
  synchronize(a.path,a.session());synchronize(b.path,b.session());b.resume(b.session());self.assertEqual(a.yubikey_enrollments(),b.yubikey_enrollments())
  a.rename_yubikey(a.yubikey_enrollments()[0]['id'],'Desktop');b.remove_yubikey(b.yubikey_enrollments()[1]['id'])
  synchronize(a.path,a.session())
  with self.assertRaises(SyncConflict):synchronize(b.path,b.session())
  a.lock();b.lock()
 def test_unsupported_collection_fails_closed(self):
  for raw in [b'{"version":2,"keys":[{}]}',b'{"version":9}',b'{"version":2,"keys":{}}']:
   with self.assertRaises(VaultError):decode(raw)

if __name__=='__main__':unittest.main()
