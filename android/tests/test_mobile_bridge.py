"""Desktop-produced format-2 snapshots exercised through the Android adapter."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/python'
sys.path.insert(0, str(SOURCE))
import mobile_bridge as mobile
from managed_vault import ManagedVault
from vault import VaultError

PASSWORD = 'Synthetic-only-Password2026!'


class Interoperability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temporary.name)
        cls.personal = cls.base / 'personal.db'
        vault = ManagedVault(cls.personal)
        vault.create(PASSWORD)
        cls.personal_id = vault.save({'description': 'Example Café', 'user_name': 'tester',
                                     'link': 'https://example.invalid', 'password': 'NeverSearchSecret900', 'notes': 'invented'})
        vault.lock()
        cls.managed = cls.base / 'managed.db'
        vault = ManagedVault(cls.managed)
        vault.create(PASSWORD, managed=True)
        cls.visible_id = vault.save({'description': 'Shared synthetic entry', 'password': 'shared-dummy'})
        cls.hidden_id = vault.save({'description': 'Excluded synthetic entry', 'password': 'hidden-dummy'})
        cls.uid = vault.add_user('Straße', PASSWORD)
        vault.set_excluded(cls.hidden_id, cls.uid, True)
        vault.lock()

    @classmethod
    def tearDownClass(cls):
        mobile.lock()
        cls.temporary.cleanup()

    def tearDown(self):
        mobile.lock()

    def test_personal_snapshot_is_read_only(self):
        before = hashlib.sha256(self.personal.read_bytes()).digest()
        self.assertTrue(json.loads(mobile.validate_file(str(self.personal)))['personal'])
        records = json.loads(mobile.unlock(str(self.personal), '', PASSWORD))
        self.assertEqual(records[0]['description'], 'Example Café')
        self.assertNotIn('password', records[0])
        self.assertNotIn('notes', records[0])
        self.assertEqual(json.loads(mobile.detail(self.personal_id))['password'], 'NeverSearchSecret900')
        with self.assertRaises(sqlite3.OperationalError):
            mobile._vault.db.execute("DELETE FROM entries")
        self.assertEqual(hashlib.sha256(self.personal.read_bytes()).digest(), before)

    def test_search_never_matches_secrets(self):
        mobile.unlock(str(self.personal), '', PASSWORD)
        self.assertEqual(json.loads(mobile.list_entries('NeverSearchSecret900')), [])
        self.assertEqual(json.loads(mobile.list_entries('invented')), [])
        self.assertEqual(len(json.loads(mobile.list_entries('café TESTER'))), 1)

    def test_unicode_account_and_exclusion(self):
        records = json.loads(mobile.unlock(str(self.managed), ' STRASSE ', PASSWORD))
        self.assertEqual([r['id'] for r in records], [self.visible_id])
        with self.assertRaises(VaultError):
            mobile.detail(self.hidden_id)

    def test_bad_password_locks_everything(self):
        mobile.unlock(str(self.personal), '', PASSWORD)
        with self.assertRaises(VaultError):
            mobile.unlock(str(self.personal), '', 'incorrect')
        with self.assertRaises(VaultError):
            mobile.detail(self.personal_id)

    def test_tampered_policy_is_rejected_at_import(self):
        path = self.base / 'policy-tampered.db'
        shutil.copy2(self.personal, path)
        with sqlite3.connect(path) as db:
            db.execute("UPDATE metadata SET value=? WHERE name='vault_id'", (b'changed',))
        with self.assertRaises(VaultError):
            mobile.validate_file(str(path))

    def test_tampered_entry_blocks_unlock(self):
        path = self.base / 'entry-tampered.db'
        shutil.copy2(self.personal, path)
        with sqlite3.connect(path) as db:
            payload = json.loads(db.execute('SELECT payload FROM entries').fetchone()[0])
            payload['ciphertext'] = 'AAAA'
            db.execute('UPDATE entries SET payload=?', (json.dumps(payload).encode(),))
        with self.assertRaises(VaultError):
            mobile.unlock(str(path), '', PASSWORD)
        self.assertIsNone(mobile._vault)

    def test_disabled_account_is_rejected(self):
        path = self.base / 'disabled.db'
        shutil.copy2(self.managed, path)
        vault = ManagedVault(path)
        vault.unlock(PASSWORD, 'Manager')
        vault.set_disabled(self.uid, True)
        vault.lock()
        with self.assertRaises(VaultError):
            mobile.unlock(str(path), 'Straße', PASSWORD)

    def test_explicit_lock_removes_session(self):
        mobile.unlock(str(self.personal), '', PASSWORD)
        mobile.lock()
        with self.assertRaises(VaultError):
            mobile.list_entries('')

    def nas_copies(self):
        folder = Path(tempfile.mkdtemp(dir=self.base))
        local = folder / 'phone.db'
        remote = folder / 'nas.db'
        shutil.copy2(self.personal, local)
        shutil.copy2(self.personal, remote)
        mobile.unlock(str(local), '', PASSWORD)
        return local, remote

    def test_nas_refresh_authenticates_and_keeps_encrypted_backup(self):
        local, remote = self.nas_copies()
        before = local.read_bytes()
        vault = ManagedVault(remote)
        vault.unlock(PASSWORD)
        vault.save({'id': self.personal_id, 'description': 'Changed on Linux', 'password': 'New-synthetic-secret'})
        vault.lock()
        result = json.loads(mobile.apply_nas_snapshot(str(remote), str(local)))
        self.assertFalse(result['revoked'])
        self.assertEqual(json.loads(mobile.detail(self.personal_id))['password'], 'New-synthetic-secret')
        backups = list((local.parent / 'nas-backups').glob('*.sqlite'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        self.assertNotIn(b'New-synthetic-secret', local.read_bytes())

    def test_nas_wrong_vault_leaves_phone_unchanged(self):
        local, remote = self.nas_copies()
        remote.unlink()
        vault = ManagedVault(remote)
        vault.create(PASSWORD)
        vault.lock()
        before = local.read_bytes()
        with self.assertRaises(VaultError):
            mobile.apply_nas_snapshot(str(remote), str(local))
        self.assertEqual(local.read_bytes(), before)
        self.assertTrue(mobile.session_ready())

    def test_nas_bad_entry_never_replaces_phone(self):
        local, remote = self.nas_copies()
        before = local.read_bytes()
        with sqlite3.connect(remote) as db:
            payload = json.loads(db.execute('SELECT payload FROM entries').fetchone()[0])
            payload['ciphertext'] = 'AAAA'
            db.execute('UPDATE entries SET payload=?', (json.dumps(payload).encode(),))
        with self.assertRaises(Exception):
            mobile.apply_nas_snapshot(str(remote), str(local))
        self.assertEqual(local.read_bytes(), before)
        self.assertTrue(mobile.session_ready())

    def test_nas_canceled_refresh_keeps_phone_copy(self):
        local, remote = self.nas_copies()
        before = local.read_bytes()
        class Guard:
            def getAsBoolean(self): return False
        with self.assertRaises(VaultError):
            mobile.apply_nas_snapshot(str(remote), str(local), Guard())
        self.assertEqual(local.read_bytes(), before)

    def test_nas_does_not_replace_sample_session(self):
        local, remote = self.nas_copies()
        mobile.unlock(str(self.personal), '', PASSWORD)
        with self.assertRaises(VaultError):
            mobile.apply_nas_snapshot(str(remote), str(local))

    def test_nas_revocation_is_adopted_and_locks_session(self):
        folder = Path(tempfile.mkdtemp(dir=self.base))
        local, remote = folder / 'phone.db', folder / 'nas.db'
        shutil.copy2(self.managed, local); shutil.copy2(self.managed, remote)
        mobile.unlock(str(local), 'Straße', PASSWORD)
        vault = ManagedVault(remote); vault.unlock(PASSWORD, 'Manager')
        vault.set_disabled(self.uid, True); vault.lock()
        result = json.loads(mobile.apply_nas_snapshot(str(remote), str(local)))
        self.assertTrue(result['revoked'])
        self.assertFalse(mobile.session_ready())
        with self.assertRaises(VaultError):
            mobile.unlock(str(local), 'Straße', PASSWORD)


if __name__ == '__main__':
    unittest.main(verbosity=2)
