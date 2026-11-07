"""Crypto/storage checks. Physical transport, PIN and touch require device tests."""
import base64, json, os, pathlib, sqlite3, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'android-shared/python'),str(ROOT/'android/app/src/main/python'),str(ROOT/'android-standalone/app/src/main/python')]
import pocket, mobile_bridge as network
from managed_vault import ManagedVault
from vault import VaultError
b64=lambda x:base64.b64encode(x).decode()
PW='Invented-Only-Master-Password!'

class HardwareTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'vault.sqlite'
  self.credential=os.urandom(128);self.salt=os.urandom(32);self.secret=os.urandom(32)
 def tearDown(self):
  pocket.lock();network.lock();self.tmp.cleanup()
 def create(self,managed=False):
  v=ManagedVault(self.path);v.create(PW,managed=managed,username='Owner',vault_name='Invented fixture')
  v.save({'description':'Invented entry','password':'SyntheticSecret-Only'})
  v.enroll_yubikey(self.credential,self.salt,self.secret);v.lock()
 def test_network_unlock_and_password_fallback(self):
  self.create();r=network.hardware_request(self.path,'');records=json.loads(network.unlock_hardware(self.path,'',r,b64(self.secret)))
  self.assertEqual(records[0]['description'],'Invented entry');network.lock()
  self.assertEqual(len(json.loads(network.unlock(self.path,'',PW))),1)
 def test_wrong_key_and_malformed_output_leave_locked(self):
  self.create();r=network.hardware_request(self.path,'')
  for value in [b64(os.urandom(32)),b64(b'short'),'not-base64!']:
   with self.assertRaises(VaultError):network.unlock_hardware(self.path,'',r,value)
   self.assertIsNone(network._vault)
  self.assertEqual(len(json.loads(network.unlock(self.path,'',PW))),1)
 def test_stale_enrollment_and_request_tampering(self):
  self.create();r=network.hardware_request(self.path,'');changed=json.loads(r);changed['salt']=b64(os.urandom(32))
  with self.assertRaises(VaultError):network.unlock_hardware(self.path,'',json.dumps(changed),b64(self.secret))
  v=ManagedVault(self.path);v.unlock(PW);v.enroll_yubikey(os.urandom(128),os.urandom(32),os.urandom(32));v.lock()
  with self.assertRaises(VaultError):network.unlock_hardware(self.path,'',r,b64(self.secret))
  self.assertIsNone(network._vault)
 def test_managed_account_binding(self):
  self.create(managed=True);v=ManagedVault(self.path);v.unlock(PW,'Owner');v.add_user('Other',PW);v.lock()
  r=network.hardware_request(self.path,'Owner')
  with self.assertRaises(VaultError):network.unlock_hardware(self.path,'Other',r,b64(self.secret))
  self.assertIsNone(network._vault)
  self.assertEqual(len(json.loads(network.unlock_hardware(self.path,'Owner',r,b64(self.secret)))),1)
 def test_pocket_enroll_unlock_export_restore_and_replacement_refusal(self):
  pocket.create(self.path,PW,'Invented Pocket');pocket.save(json.dumps({'description':'Pocket entry','password':'InventedOnly'}))
  data={'credential':b64(self.credential),'salt':b64(self.salt),'response':b64(self.secret)}
  pocket.enroll_hardware(json.dumps(data));self.assertTrue(self.path.with_name('vault-before-yubikey.sqlite').exists())
  with self.assertRaises(VaultError):pocket.enroll_hardware(json.dumps(data))
  r=pocket.hardware_request(self.path);pocket.lock();pocket.unlock_hardware(self.path,r,b64(self.secret))
  self.assertEqual(len(json.loads(pocket.listing(''))),1)
  export=self.path.with_name('export.sqlite');pocket.export(export,PW);pocket.lock()
  restored=self.path.with_name('restored.sqlite');pocket.restore(export,restored,PW,'NewLocalSecret-Only')
  # Format-2 backup retains the hardware envelope; restoring must still validate it.
  r=pocket.hardware_request(restored);pocket.unlock_hardware(restored,r,b64(self.secret))
  self.assertEqual(len(json.loads(pocket.listing(''))),1)
  pocket.lock();pocket.unlock(restored,'NewLocalSecret-Only')
 def test_pocket_wrong_key_no_session(self):
  self.create();r=pocket.hardware_request(self.path)
  with self.assertRaises(VaultError):pocket.unlock_hardware(self.path,r,b64(os.urandom(32)))
  self.assertIsNone(pocket._vault)
 def test_no_enrollment_is_read_only(self):
  v=ManagedVault(self.path);v.create(PW,vault_name='Fixture');v.lock();before=self.path.read_bytes()
  with self.assertRaises(VaultError):network.hardware_request(self.path,'')
  self.assertEqual(before,self.path.read_bytes())

if __name__=='__main__':unittest.main()
