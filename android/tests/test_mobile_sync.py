import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/src/main/python'))
import mobile_bridge as mobile
import mobile_sync as sync
from managed_vault import ManagedVault
from vault import VaultError

class TwoWaySync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed=tempfile.TemporaryDirectory(); cls.origin=Path(cls.seed.name)/'seed.db'
        v=ManagedVault(cls.origin); v.create('Synthetic-sync-only!'); cls.eid=v.save({'description':'Original','password':'dummy'}); cls.session=v.session(); v.lock()
    @classmethod
    def tearDownClass(cls): cls.seed.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.local=self.root/'local.db'; self.remote=self.root/'remote.db'; self.result=self.root/'result.db'
        shutil.copyfile(self.origin,self.local); shutil.copyfile(self.origin,self.remote)
        plan=self.prepare(); sync.commit(self.local,self.result,plan)
    def tearDown(self): mobile.lock(); self.temp.cleanup()
    def prepare(self,**kw): return sync.prepare(self.local,self.remote,self.result,self.session,'nas/share/folder',**kw)
    def edit(self,path,description,eid=None):
        v=ManagedVault(path); v.resume(self.session)
        try: return v.save({'id':eid or self.eid,'description':description,'password':'dummy'})
        finally: v.lock()
    def test_phone_upload_prepared_without_advancing_baseline(self):
        before=sync.read_config(self.local); self.edit(self.local,'Phone')
        plan=self.prepare(); self.assertTrue(plan['upload']); self.assertEqual(sync.read_config(self.local),before)
        self.assertEqual(sync.state(self.remote),before['baseline'])
        shutil.copyfile(self.result,self.remote); sync.commit(self.local,self.result,plan)
        self.assertEqual(sync.read_config(self.local)['baseline'],sync.state(self.remote))
    def test_remote_download(self):
        self.edit(self.remote,'NAS'); plan=self.prepare(); self.assertFalse(plan['upload']); self.assertTrue(plan['replace_local'])
        sync.commit(self.local,self.result,plan); self.assertEqual(sync.state(self.local),sync.state(self.remote))
    def test_independent_changes_merge(self):
        self.edit(self.local,'Phone'); v=ManagedVault(self.remote); v.resume(self.session)
        other=v.save({'description':'NAS new','password':'dummy'}); v.lock()
        plan=self.prepare(); self.assertTrue(plan['upload']); self.assertEqual(set(plan['baseline']['entries']),{self.eid,other})
    def test_competing_changes_require_review(self):
        self.edit(self.local,'Phone'); self.edit(self.remote,'NAS'); plan=self.prepare()
        self.assertFalse(plan['ready']); self.assertEqual(plan['conflicts'][0]['phone'],'Phone')
        chosen=self.prepare(choices={self.eid:'shared'},expected=plan['expected']); self.assertFalse(chosen['upload'])
        sync.commit(self.local,self.result,chosen); self.assertEqual(sync.state(self.local),sync.state(self.remote))
    def test_changed_copy_invalidates_review(self):
        self.edit(self.local,'Phone'); self.edit(self.remote,'NAS'); plan=self.prepare(); self.edit(self.remote,'New NAS')
        with self.assertRaises(VaultError): self.prepare(choices={self.eid:'local'},expected=plan['expected'])
    def test_changed_phone_prevents_commit(self):
        self.edit(self.local,'Phone'); plan=self.prepare(); self.edit(self.local,'Later phone')
        with self.assertRaises(VaultError): sync.commit(self.local,self.result,plan)
    def test_endpoint_change_preserves_pending_edits(self):
        self.edit(self.local,'Phone')
        with self.assertRaises(VaultError): sync.prepare(self.local,self.remote,self.result,self.session,'other')
    def test_editing_gate_and_sample_save_delete(self):
        sync.config_path(self.local).unlink(); mobile.unlock(str(self.local),'','Synthetic-sync-only!',True,False)
        with self.assertRaises(VaultError): mobile.save_entry(json.dumps({'description':'Blocked'}))
        mobile.lock(); mobile.unlock(str(self.local),'','Synthetic-sync-only!',True,True)
        eid=mobile.save_entry(json.dumps({'description':'Sample new','password':'dummy'})); mobile.delete_entry(eid)
        self.assertNotIn(eid,[r['id'] for r in json.loads(mobile.list_entries(''))])
