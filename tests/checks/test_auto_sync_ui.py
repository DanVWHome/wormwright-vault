import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app import Window
from vault import Vault
from sync import configure, fingerprint, read_settings
app=QApplication([])
def wait_for(predicate):
    deadline=time.monotonic()+10
    while not predicate():
        app.processEvents()
        if time.monotonic()>deadline:raise AssertionError('Background sync did not finish')
        time.sleep(.01)
with tempfile.TemporaryDirectory() as name:
    os.environ['XDG_DATA_HOME']=name
    root=Path(name);share=root/'share';share.mkdir()
    seed=Vault(root/'dummy.sqlite');seed.create('dummy-test-password')
    seed.save({'description':'Mail','password':'dummy','link':'','user_name':'','notes':''})
    configure(seed,share,2,True,5);seed.lock()
    w=Window(seed.path);w.show();w.master.setText('dummy-test-password')
    w.unlock() # queues startup sync after authentication
    wait_for(lambda:(share/'wormwright-vault.sqlite').exists() and w.sync_task is None)
    assert w.vault.unlocked and w.auto_timer.interval()==5000
    assert fingerprint(seed.path)==fingerprint(share/'wormwright-vault.sqlite')
    assert read_settings(w.vault)['interval']==5
    from auto_sync import synchronize as real_sync
    def slow_sync(*args,**kwargs):
        time.sleep(.15)
        return real_sync(*args,**kwargs)
    beats=[];heartbeat=QTimer();heartbeat.timeout.connect(lambda:beats.append(1));heartbeat.start(10)
    with patch('auto_sync.synchronize',side_effect=slow_sync):
        assert w.auto_sync()
        wait_for(lambda:w.sync_task is None)
    assert len(beats)>3,'Network work blocked the GUI'
    heartbeat.stop()
    record=w.vault.entries()[0];w.vault.save({**record,'notes':'final edit'})
    with patch('app.QMessageBox.warning'):
        w.close()
        wait_for(lambda:w.sync_task is None and not w.isVisible())
    assert not w.vault.unlocked
    assert fingerprint(seed.path)==fingerprint(share/'wormwright-vault.sqlite')
    remote=Vault(share/'wormwright-vault.sqlite');remote.unlock('dummy-test-password')
    remote.save({**record,'notes':'arrives at locked startup'});remote.lock()
    locked=Window(seed.path);locked.show()
    wait_for(lambda:locked.sync_task is None and fingerprint(seed.path)==fingerprint(share/'wormwright-vault.sqlite'))
    assert not locked.vault.unlocked and locked.table.rowCount()==0 and not locked.lock_timer.isActive()
    locked.close();wait_for(lambda:locked.sync_task is None and not locked.isVisible())
    assert not locked.vault.unlocked
print('Startup after unlock, interval, GUI responsiveness and final close sync passed.')
