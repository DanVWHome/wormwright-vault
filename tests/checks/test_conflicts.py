"""Explicit resolution with distinct keys, stale copies, cancel and encrypted backups."""
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from vault import Vault, VaultError
from sync import configure, synchronize, fingerprint
from conflicts import Comparison

with tempfile.TemporaryDirectory() as name:
    root = Path(name); share = root / 'share'; share.mkdir()
    master = Vault(share / 'wormwright-vault.sqlite'); master.create('shared-dummy-password')
    master.save({'description':'Shared mail','password':'secret-shared','link':'','user_name':'','notes':''}); master.lock()
    local = Vault(root / 'local.sqlite'); local.create('local-dummy-password')
    local.save({'description':'Local mail','password':'secret-local','link':'','user_name':'','notes':''})
    configure(local, share, 2)
    before = fingerprint(local.path), fingerprint(master.path)
    cancelled = Comparison(local); cancelled.unlock_shared('shared-dummy-password'); cancelled.compare(); cancelled.close()
    assert before == (fingerprint(local.path), fingerprint(master.path))
    c = Comparison(local); c.unlock_shared('shared-dummy-password'); rows = c.compare()
    choices = ['local' if ours else 'shared' for _, ours, theirs in rows]
    safety = c.apply(choices); c.close()
    assert all(p.is_file() for p in safety)
    local.unlock('shared-dummy-password'); assert len(local.entries()) == 2
    assert synchronize(local).startswith('Already')
    assert b'secret-local' not in local.path.read_bytes()
    c = Comparison(local); c.unlock_shared('shared-dummy-password'); c.compare()
    local.save({'description':'Late edit','password':'dummy','link':'','user_name':'','notes':''})
    stale_before = fingerprint(local.path), fingerprint(master.path)
    try:
        c.apply(['shared'] * len(c.rows)); raise AssertionError('Stale comparison overwrote changes')
    except VaultError as e:
        assert 'changed while' in str(e)
    c.close()
    assert stale_before == (fingerprint(local.path), fingerprint(master.path))
    # Resolve related copies with a changed password and an explicit omission.
    mail = next(r for r in local.entries() if r['description'] == 'Shared mail')
    local.save({**mail, 'password': 'new-local-password'})
    c = Comparison(local); c.unlock_shared('shared-dummy-password'); rows = c.compare()
    choices = ['local' if (ours or theirs)['description'] == 'Shared mail' else 'omit' for _, ours, theirs in rows]
    c.apply(choices); c.close()
    local.unlock('shared-dummy-password')
    assert len(local.entries()) == 1 and local.entries()[0]['password'] == 'new-local-password'
    assert synchronize(local).startswith('Already')
    original = Vault(safety[0]); original.unlock('local-dummy-password')
    assert original.entries()[0]['description'] == 'Local mail'; original.lock()
    local.lock()
print('Conflict resolution, distinct keys, cancel, stale detection and backup checks passed.')
