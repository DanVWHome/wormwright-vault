"""Update metadata cannot redirect downloads, mislabel channels or expose secrets."""
import json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication,QMenu,QWidget
import update_check as updates
assert updates.version_key('0.3.4-preview.1') < updates.version_key('0.3.4') < updates.version_key('0.3.5-preview.1')
assert updates.version_key('0.3.4-preview.2') > updates.version_key('0.3.4-preview.1')
for bad in ['1.2','1.2.3-evil','01.2.3',None]:
 try:updates.version_key(bad)
 except ValueError:pass
 else:raise AssertionError(bad)
feed={'schema':1,'channels':{'stable':None,'preview':{'version':'0.3.5-preview.1','notes':'Release notes','url':'https://attacker.invalid'}}}
assert updates.release_from_feed(json.dumps(feed).encode(),'stable') is None
assert updates.release_from_feed(json.dumps(feed).encode(),'preview')['version']=='0.3.5-preview.1'
for bad in [b'bad json',b'x'*65537,json.dumps({'schema':2}).encode(),json.dumps({'schema':1,'channels':{'stable':feed['channels']['preview']}}).encode()]:
 try:updates.release_from_feed(bad,'stable')
 except ValueError:pass
 else:raise AssertionError('Invalid metadata accepted')
assert updates.DOWNLOAD_URL=='https://wormwright.com/vault-windows.html'
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as d,patch.object(updates,'settings_path',return_value=Path(d)/'updates.json'):
 assert not updates.read_settings()['automatic']
 checker=updates.UpdateChecker(app);checker.timer.stop()
 checker.save({'automatic':True,'channel':'preview','last_check':0})
 with patch.object(checker,'check') as check:
  checker.automatic();check.assert_called_once()
 checker.save({'automatic':True,'channel':'preview','last_check':updates.time.time()})
 with patch.object(checker,'check') as check:
  checker.automatic();check.assert_not_called()
 menu=QMenu();owner=QWidget()
 with patch.object(updates.sys,'platform','win32'),patch.object(updates,'_checker',checker),patch.object(checker,'check') as check:
  updates.add_update_actions(menu,owner)
  assert [a.text() for a in menu.actions()]==['Check for Updates…','Update Settings…']
  menu.actions()[0].trigger();check.assert_called_once_with(owner)
print('PASS: version ordering, channel validation, bounded response, fixed download URL, opt-in daily checks and Windows menu actions')
