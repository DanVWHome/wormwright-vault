"""Three-device edits, deletions, conflicts, locked merging and interrupted apply."""
import sys
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from vault import Vault
from sync import configure, synchronize, SyncConflict, read_settings, fingerprint, atomic_json, settings_path
from auto_sync import AutoSyncTask, finish_sync

with tempfile.TemporaryDirectory() as name:
    root = Path(name); share = root / 'share'; share.mkdir()
    a = Vault(root/'a.sqlite'); a.create('dummy-test-password')
    one = a.save({'description':'Mail', 'password':'dummy-mail', 'notes':''})
    two = a.save({'description':'Router', 'password':'dummy-router', 'notes':''})
    records = a.entries(); one, two = records
    configure(a,share,2); synchronize(a)
    b = Vault(root/'b.sqlite'); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    configure(b,share,2); synchronize(b)
    c = Vault(root/'c.sqlite'); shutil.copyfile(a.path,c.path); c.unlock('dummy-test-password')
    configure(c,share,2); synchronize(c)
    a.save({**one,'notes':'desktop edit'}); synchronize(a)
    b.save({**two,'notes':'laptop edit'})
    assert synchronize(b).startswith('Merged')
    synchronize(a); synchronize(c)
    assert fingerprint(a.path)==fingerprint(b.path)==fingerprint(c.path)
    assert {r['notes'] for r in c.entries()} == {'desktop edit','laptop edit'}
    # Delete versus an independent addition merges without resurrecting the deletion.
    one, two = b.entries()
    a.delete(one['id']); synchronize(a)
    b.save({'description':'New', 'password':'dummy-new','notes':''})
    assert synchronize(b).startswith('Merged')
    synchronize(c)
    assert one['id'] not in {r['id'] for r in c.entries()}
    # Delete versus edit requires review and preserves both files exactly.
    target = b.entries()[0]
    a.lock(); a.unlock('dummy-test-password'); synchronize(a)
    a.delete(target['id']); synchronize(a)
    b.save({**target,'notes':'edited offline'})
    before = fingerprint(b.path); remote = fingerprint(share/'wormwright-vault.sqlite')
    try: synchronize(b)
    except SyncConflict: pass
    else: raise AssertionError('Delete/edit conflict must not merge')
    assert fingerprint(b.path)==before and fingerprint(share/'wormwright-vault.sqlite')==remote
    # Rejoin a clean copy, then merge through the locked background snapshot path.
    b.lock(); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    atomic_json(settings_path(b), {'folder':str(share),'limit':2})
    synchronize(b)
    synchronize(c)
    left = a.entries()[0]
    a.save({**left,'notes':'shared again'}); synchronize(a)
    b.save({'description':'Locked addition','password':'dummy-locked','notes':''}); b.lock()
    task = AutoSyncTask(b,read_settings(b)); task.run()
    assert task.error is None and task.result.startswith('Merged') and task.key is None
    finish_sync(b,task); task.cleanup()
    assert not b.unlocked
    b.unlock('dummy-test-password')
    assert 'Locked addition' in {r['description'] for r in b.entries()}
    # Upgrade: missing history never guesses at competing changes.
    config = read_settings(b); config.pop('entry_history'); atomic_json(settings_path(b),config)
    a.save({'description':'Other','password':'dummy-other','notes':''}); synchronize(a)
    b.save({'description':'Local','password':'dummy-local','notes':''})
    try: synchronize(b)
    except SyncConflict: pass
    else: raise AssertionError('Missing history requires review')
    a.lock(); b.lock(); c.lock()
print('Independent edits, deletion/addition, deletion/edit conflict, third device, locked merge and upgrade passed.')

from unittest.mock import patch
with tempfile.TemporaryDirectory() as name:
    root=Path(name); share=root/'share'; share.mkdir()
    a=Vault(root/'a.sqlite'); a.create('dummy-test-password')
    a.save({'description':'A','password':'dummy-A','notes':''})
    a.save({'description':'B','password':'dummy-B','notes':''})
    configure(a,share,2); synchronize(a)
    b=Vault(root/'b.sqlite'); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    configure(b,share,2); synchronize(b)
    first, second=a.entries()
    a.save({**first,'notes':'server edit'}); synchronize(a)
    b.save({**second,'notes':'snapshot edit'})
    task=AutoSyncTask(b,read_settings(b)); task.run()
    assert task.error is None and task.result.startswith('Merged')
    b.save({**second,'notes':'newer local edit'})
    current=fingerprint(b.path); old_settings=read_settings(b)
    try: finish_sync(b,task)
    except SyncConflict: pass
    else: raise AssertionError('Concurrent edit must block merged replacement')
    assert fingerprint(b.path)==current and read_settings(b)==old_settings
    task.cleanup()
    a.lock(); b.lock()
print('Concurrent edit after a merged transfer preserves local data and baseline.')

with tempfile.TemporaryDirectory() as name:
    root=Path(name); share=root/'share'; share.mkdir()
    a=Vault(root/'a.sqlite'); a.create('dummy-test-password')
    a.save({'description':'Mail','password':'history-must-not-contain-this','notes':'private note'})
    configure(a,share,2); synchronize(a)
    assert 'history-must-not-contain-this' not in settings_path(a).read_text()
    assert 'private note' not in settings_path(a).read_text()
    b=Vault(root/'b.sqlite'); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    configure(b,share,2); synchronize(b)
    record=a.entries()[0]
    a.save({**record,'notes':'changed by a'}); synchronize(a)
    b.save({**record,'notes':'changed by b'})
    try: synchronize(b)
    except SyncConflict: pass
    else: raise AssertionError('Competing same-entry edits require review')
    # Recover b to current baseline and simulate a failed merged publication.
    b.lock(); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    atomic_json(settings_path(b), {'folder':str(share),'limit':2}); synchronize(b)
    a.save({**record,'notes':'new shared change'}); synchronize(a)
    b.save({'description':'Offline new','password':'dummy-offline','notes':''})
    local_hash=fingerprint(b.path); shared_hash=fingerprint(share/'wormwright-vault.sqlite')
    before=read_settings(b)
    import os
    replace=os.replace
    def fail_remote(source,destination):
        if Path(destination)==share/'wormwright-vault.sqlite':
            raise OSError('Simulated interrupted transfer')
        return replace(source,destination)
    with patch('sync.os.replace',side_effect=fail_remote):
        try: synchronize(b)
        except OSError: pass
        else: raise AssertionError('Expected simulated transfer failure')
    assert fingerprint(b.path)==local_hash and fingerprint(share/'wormwright-vault.sqlite')==shared_hash
    assert read_settings(b)==before and not (share/'.wormwright-sync-lock').exists()
    assert synchronize(b).startswith('Merged')
    a.lock(); b.lock()
print('Same-entry conflict, no plaintext history, interrupted merge and retry passed.')
