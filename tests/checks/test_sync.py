"""Fictional vaults only: offline changes, conflicts and retention."""
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from vault import Vault, VaultError
from sync import configure, synchronize, fingerprint

with tempfile.TemporaryDirectory() as name:
    root = Path(name)
    share = root / 'share'; share.mkdir()
    a = Vault(root / 'a.sqlite'); a.create('disposable-test-password')
    entry = {'description': 'Demo Mail', 'password': 'fictional', 'notes': ''}
    identity = a.save(entry)
    configure(a, share, 2)
    assert synchronize(a).startswith('Uploaded')
    b = Vault(root / 'b.sqlite'); a.backup(b.path); b.unlock('disposable-test-password')
    configure(b, share, 2)
    assert synchronize(b).startswith('Already')
    for index in range(4):
        a.save({**entry, 'id': identity, 'notes': str(index)})
        assert synchronize(a).startswith('Uploaded')
    assert len(list((share / '.wormwright-sync-backups').glob('*.sqlite'))) == 2
    assert len(list((root / '.wormwright-sync-backups').glob('*.sqlite'))) == 2
    assert synchronize(b).startswith('Downloaded')
    assert not b.unlocked
    b.unlock('disposable-test-password')
    assert b.entries()[0]['notes'] == '3'
    a.save({**entry, 'id': identity, 'notes': 'from laptop'})
    b.save({**entry, 'id': identity, 'notes': 'from desktop'})
    synchronize(a)
    before = fingerprint(b.path), fingerprint(share / 'wormwright-vault.sqlite')
    try:
        synchronize(b)
        raise AssertionError('Conflict was overwritten')
    except VaultError:
        pass
    assert before == (fingerprint(b.path), fingerprint(share / 'wormwright-vault.sqlite'))
    (share / '.wormwright-sync-lock').mkdir()
    try:
        synchronize(a)
        raise AssertionError('Lock was ignored')
    except VaultError:
        pass
    (share / '.wormwright-sync-lock').rmdir()
    a.lock(); b.lock()
print('Sync conflict, download, lock and retention checks passed.')
