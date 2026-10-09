"""Saving the same endpoint retains managed ancestry; changing it unpairs."""
from pathlib import Path
import sys,tempfile
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sync import configure,read_settings,atomic_json,settings_path
with tempfile.TemporaryDirectory() as name:
 root=Path(name);folder=root/'shared';folder.mkdir();other=root/'other';other.mkdir()
 vault=SimpleNamespace(path=root/'local.sqlite')
 baseline={'identity':['synthetic','key'],'admin':'hash','entries':{'entry':'hash'}}
 atomic_json(settings_path(vault),{'folder':str(folder),'managed_baseline':baseline,'baseline':'legacy','entry_history':{'dummy':'hash'}})
 configure(vault,str(folder),10,True,30)
 assert read_settings(vault)['managed_baseline']==baseline
 assert read_settings(vault)['baseline']=='legacy'
 configure(vault,str(folder),20,False,60)
 assert read_settings(vault)['managed_baseline']==baseline
 configure(vault,str(other),10)
 assert 'managed_baseline' not in read_settings(vault)
print('PASS: unchanged folder retains managed baseline; changed folder unpairs.')

from managed_sync import combined
local={'identity':['vault','key'],'admin':'same','entries':{'unchanged':'a','changed':'b','local-only':'c'}}
remote={'identity':['vault','key'],'admin':'same','entries':{'unchanged':'a','changed':'d'}}
assert combined(None,local,remote)=={'unchanged':'local','changed':None,'local-only':None}
print('PASS: missing baseline retains identical entries and reviews differing entries.')
