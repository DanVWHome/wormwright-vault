"""Snapshot worker, concurrent edits, locked completion and retained backups."""
import tempfile
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtCore import QCoreApplication
from vault import Vault
from sync import configure, synchronize, fingerprint, SyncConflict, read_settings
from auto_sync import AutoSyncTask, finish_sync
app=QCoreApplication([])
with tempfile.TemporaryDirectory() as name:
    root=Path(name); share=root/'share'; share.mkdir()
    a=Vault(root/'a.sqlite'); a.create('dummy-test-password')
    identity=a.save({'description':'Mail','password':'dummy','link':'','user_name':'','notes':'initial'})
    configure(a,share,2,True,30)
    task=AutoSyncTask(a,read_settings(a));task.run(); assert not task.error
    finish_sync(a,task);task.cleanup()
    b=Vault(root/'b.sqlite');a.backup(b.path);b.unlock('dummy-test-password');configure(b,share,2);synchronize(b)
    record=a.entries()[0]
    a.save({**record,'notes':'new'})
    task=AutoSyncTask(a,read_settings(a));task.run()
    a.save({**record,'notes':'newer while uploading'})
    assert finish_sync(a,task);task.cleanup()
    assert a.entries()[0]['notes']=='newer while uploading'
    task=AutoSyncTask(a,read_settings(a));task.run();finish_sync(a,task);task.cleanup()
    task=AutoSyncTask(b,read_settings(b));task.run();assert task.result.startswith('Downloaded')
    finish_sync(b,task);task.cleanup()
    assert b.unlocked and b.entries()[0]['notes']=='newer while uploading'
    a.save({**record,'notes':'remote again'});synchronize(a)
    task=AutoSyncTask(b,read_settings(b));task.run()
    b.save({**record,'notes':'local while downloading'})
    before=fingerprint(b.path)
    try:
        finish_sync(b,task);raise AssertionError('Concurrent edit overwritten')
    except SyncConflict:pass
    assert fingerprint(b.path)==before;task.cleanup()
    # Restore paired local snapshot for a locked completion test.
    b.lock();b.path.unlink();a.backup(b.path);b.unlock('dummy-test-password');configure(b,share,2);synchronize(b)
    a.save({**record,'notes':'download while locked'});synchronize(a)
    task=AutoSyncTask(b,read_settings(b));task.run();b.lock();finish_sync(b,task);task.cleanup()
    assert not b.unlocked;b.unlock('dummy-test-password');assert b.entries()[0]['notes']=='download while locked'
    a.save({**record,'notes':'fully locked sync'});synchronize(a);b.lock()
    task=AutoSyncTask(b,read_settings(b));assert task.key is None
    task.run();assert task.error is None
    finish_sync(b,task);task.cleanup();assert not b.unlocked
    b.unlock('dummy-test-password');assert b.entries()[0]['notes']=='fully locked sync'
    b.save({**record,'notes':'locked upload'});b.lock()
    task=AutoSyncTask(b,read_settings(b));task.run();finish_sync(b,task);task.cleanup();assert not b.unlocked
    assert fingerprint(b.path)==fingerprint(share/'wormwright-vault.sqlite')
    assert len(list((root/'.wormwright-sync-backups').glob('*.sqlite')))==4
    a.lock();b.lock()
print('Background upload/download, concurrent edit, locked completion and backup checks passed.')
