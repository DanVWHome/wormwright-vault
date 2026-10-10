import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'android-standalone/app/src/main/python'))
import pocket
from managed_vault import ManagedVault
from vault import VaultError

class PocketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.local = self.root/'local.sqlite'
        self.secret = pocket.new_secret()
        pocket.create(self.local, self.secret,"Invented test vault")
    def tearDown(self):
        pocket.lock()
        self.tmp.cleanup()
    def test_names_survive_backup_and_rename(self):
        self.assertEqual(pocket.vault_name(),'Invented test vault')
        pocket.rename_vault('Invented renamed vault')
        backup=self.root/'named-backup.sqlite';pocket.export(backup,'Invented-Backup-Password!')
        v=ManagedVault(backup);v.unlock('Invented-Backup-Password!');self.assertEqual(v.display_name,'Invented renamed vault');v.lock()
        self.assertEqual(pocket.verify_deletion(self.local,self.secret),'Invented renamed vault')
        with self.assertRaises(VaultError):pocket.create(self.root/'bad.sqlite',self.secret,' ')
        self.assertFalse((self.root/'bad.sqlite').exists())
    def entry(self):
        return {'description':'Invented Café 🔒', 'user_name':'demo@example.invalid',
                'password':'Invented-Password-Only!', 'link':'https://example.invalid/path',
                'notes':'Invented notes\nSecond line café.'}
    def test_crud_search_deletion_and_lock(self):
        record = self.entry(); eid = pocket.save(json.dumps(record))
        self.assertEqual(json.loads(pocket.listing('café demo'))[0]['id'],eid)
        self.assertEqual(json.loads(pocket.detail(eid))['notes'],record['notes'])
        record.update(id=eid, description='Changed');pocket.save(json.dumps(record))
        pocket.delete(eid);self.assertEqual(json.loads(pocket.listing('')),[])
        self.assertEqual(json.loads(pocket.deleted())[0]['id'],eid)
        pocket.recover(eid);self.assertEqual(json.loads(pocket.detail(eid))['description'],'Changed')
        pocket.lock()
        with self.assertRaises(VaultError):pocket.listing('')
        pocket.unlock(self.local,self.secret)
        self.assertEqual(len(json.loads(pocket.listing(''))),1)
    def test_optional_password_is_cryptographic(self):
        envelope=pocket.protect(self.secret,'Separate-vault-password!')
        self.assertNotIn(self.secret,envelope)
        with self.assertRaises(VaultError):pocket.unprotect(envelope,'Wrong-vault-password!')
        self.assertEqual(pocket.unprotect(envelope,'Separate-vault-password!'),self.secret)
        changed=json.loads(envelope);changed['cipher']=changed['cipher'][:-4]+'AAAA'
        with self.assertRaises(VaultError):pocket.unprotect(json.dumps(changed),'Separate-vault-password!')
    def test_fresh_phone_restore_and_wrong_secret_preserves_original(self):
        eid=pocket.save(json.dumps(self.entry()));export=self.root/'backup.sqlite'
        pocket.export(export,'Portable-backup-password!')
        original=hashlib.sha256(self.local.read_bytes()).hexdigest()
        pocket.lock(); fresh=pocket.new_secret();replacement=self.root/'fresh.sqlite'
        pocket.restore(export,replacement,'Portable-backup-password!',fresh)
        pocket.unlock(replacement,fresh)
        self.assertEqual(json.loads(pocket.detail(eid))['notes'],self.entry()['notes'])
        with self.assertRaises(Exception):pocket.restore(export,self.root/'bad.sqlite','Wrong-backup-password!',pocket.new_secret())
        self.assertFalse((self.root/'bad.sqlite').exists())
        self.assertEqual(hashlib.sha256(self.local.read_bytes()).hexdigest(),original)
        damaged=self.root/'damaged.sqlite';damaged.write_bytes(b'not a SQLite backup')
        with self.assertRaises(VaultError):pocket.restore(damaged,self.root/'bad.sqlite','Portable-backup-password!',pocket.new_secret())
        self.assertEqual(hashlib.sha256(self.local.read_bytes()).hexdigest(),original)
    def test_signed_entry_tampering_rejected(self):
        pocket.save(json.dumps(self.entry()));pocket.lock()
        with sqlite3.connect(self.local) as db:db.execute("UPDATE entries SET payload=?",(b'{}',))
        with self.assertRaises(VaultError):pocket.unlock(self.local,self.secret)
    def test_sample_is_separate(self):
        eid=pocket.save(json.dumps(self.entry()));pocket.lock()
        pocket.sample(self.root/'sample.sqlite')
        self.assertEqual(len(json.loads(pocket.listing(''))),2)
        pocket.unlock(self.local,self.secret)
        self.assertEqual(json.loads(pocket.listing(''))[0]['id'],eid)
    def test_desktop_management_and_companion_sync_roundtrip(self):
        eid=pocket.save(json.dumps(self.entry()))
        deleted=pocket.save(json.dumps({'description':'Deleted invented account','notes':'recover me'}))
        pocket.delete(deleted)
        export=self.root/'migration.sqlite';pocket.export(export,'Desktop-master-password!')
        original=hashlib.sha256(self.local.read_bytes()).hexdigest()
        # Separate process imports actual desktop engine, runs management and
        # desktop sync, then actual companion bridge and sync against shared
        # directory. This exercises protocol logic, not Android SMB transport/UI.
        subprocess.run([sys.executable,str(Path(__file__).with_name('migration_roundtrip.py')),
                        str(ROOT),str(export),eid,deleted,json.dumps(self.entry())],check=True)
        self.assertEqual(hashlib.sha256(self.local.read_bytes()).hexdigest(),original)
        pocket.lock();pocket.unlock(self.local,self.secret)
        self.assertEqual(json.loads(pocket.detail(eid))['password'],self.entry()['password'])

if __name__=='__main__':unittest.main()
