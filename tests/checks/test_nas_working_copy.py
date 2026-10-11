"""NAS opening pairs a local copy, preserves edits/settings and syncs back."""
import os,sys,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from managed_sync import synchronize,state
from nas_working_copy import prepare_managed_vault
from sync import configure,read_settings
with tempfile.TemporaryDirectory() as d:
 os.environ['XDG_DATA_HOME']=str(Path(d)/'data')
 remote=Path(d)/'gvfs/smb-share:server=192.168.1.144,share=share/PasswordVault/Dans-Vault/wormwright-vault.sqlite'
 remote.parent.mkdir(parents=True)
 v=ManagedVault(remote);v.create('dummy-nas-password');v.save({'description':'NAS entry','password':'dummy'});v.lock()
 before=hashlib.sha256(remote.read_bytes()).hexdigest()
 local=prepare_managed_vault(remote)
 assert local!=remote and local.is_relative_to(Path(d)/'data')
 working=ManagedVault(local)
 config=read_settings(working)
 assert config['folder']==str(remote.parent) and config['managed_baseline']==state(local)
 assert hashlib.sha256(remote.read_bytes()).hexdigest()==before
 assert not remote.with_name(remote.name+'.sync.json').exists()
 working.unlock('dummy-nas-password');working.save({'description':'Local edit','password':'dummy2'});working.lock()
 configure(working,remote.parent,7,False,45)
 prior=read_settings(working);prior_hash=hashlib.sha256(local.read_bytes()).hexdigest()
 assert prepare_managed_vault(remote)==local
 assert read_settings(working)==prior and hashlib.sha256(local.read_bytes()).hexdigest()==prior_hash
 working.unlock('dummy-nas-password');synchronize(local,working.session());working.lock()
 check=ManagedVault(remote);check.unlock('dummy-nas-password');assert len(check.entries())==2;check.lock()
 assert read_settings(working)['folder']==str(remote.parent)
 other=remote.parent.parent/'Other/wormwright-vault.sqlite';other.parent.mkdir();v=ManagedVault(other);v.create('other-dummy-password');v.lock()
 assert prepare_managed_vault(other)!=local
 assert prepare_managed_vault(local)==local
 print('PASS: local NAS copy, automatic pairing, baseline, no master changes on open, reopen preserves edits/preferences, real sync and independent vault isolation')
