"""Fault injection: scratch failures must not strand the shared lock."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from vault import Vault, VaultError
from sync import configure, synchronize
from sync_lock import release_lock

with tempfile.TemporaryDirectory() as name:
    root = Path(name)
    share = root / 'share'; share.mkdir()
    vault = Vault(root / 'local.sqlite'); vault.create('synthetic-lock-test-password')
    configure(vault, share, 2)
    lock = share / '.wormwright-sync-lock'
    with patch('sync.tempfile.TemporaryDirectory', side_effect=OSError('scratch unavailable')):
        try: synchronize(vault)
        except OSError: pass
        else: raise AssertionError('Expected scratch failure')
    assert not lock.exists()
    with patch('tempfile.TemporaryDirectory.cleanup', side_effect=OSError('cleanup interrupted')):
        try: synchronize(vault)
        except OSError: pass
        else: raise AssertionError('Expected cleanup failure')
    assert not lock.exists()
    synchronize(vault)
    assert not lock.exists()
    lock.mkdir()
    try: synchronize(vault)
    except VaultError: pass
    else: raise AssertionError('Existing lock must block sync')
    assert lock.exists()
    original = Path.rmdir
    calls = []
    def transient(path):
        calls.append(path)
        if len(calls) < 3: raise OSError('temporary NAS failure')
        return original(path)
    with patch.object(Path, 'rmdir', transient), patch('sync_lock.time.sleep'):
        release_lock(lock)
    assert len(calls) == 3 and not lock.exists()
    lock.mkdir()
    with patch.object(Path, 'rmdir', side_effect=OSError('NAS offline')), patch('sync_lock.time.sleep'):
        try: release_lock(lock)
        except VaultError as error: assert 'could not be removed' in str(error)
        else: raise AssertionError('Expected explicit cleanup failure')
    assert lock.exists()
    lock.rmdir(); vault.lock()
print('Sync lock failure and ownership checks passed.')
