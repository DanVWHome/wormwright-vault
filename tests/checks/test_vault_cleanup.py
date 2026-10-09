"""Permanent deletion operates on reviewed invented files only."""
from pathlib import Path
import sys,tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_vault import ManagedVault
from vault import VaultError
import vault_cleanup as cleanup
from PySide6.QtWidgets import QApplication
from managed_ui import ManagedWindow

app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as d:
    root=Path(d).resolve();path=root/'working.sqlite';v=ManagedVault(path);v.create('Invented-Deletion-Test-Password!')
    a=root/'backup-a.sqlite';b=root/'backup-b.sqlite';v.backup(a);v.backup(b)
    other=ManagedVault(root/'unrelated.sqlite');other.create('Invented-Unrelated-Password!');other.lock()
    expected=(v.meta['vault_id'],v.meta['verify'])
    found=cleanup.discover(v,[root]);assert set(found)=={a,b}
    for selected,exclude in [([root/'unrelated.sqlite'],[]),([path],[path])]:
        try:cleanup.plan(selected,expected,exclude);raise AssertionError('Unsafe file accepted')
        except VaultError:pass
    reviewed=cleanup.plan([a,b],expected,[path]);a.write_bytes(a.read_bytes()+b'changed')
    try:cleanup.remove(reviewed);raise AssertionError('Changed file deleted')
    except VaultError:assert a.exists() and b.exists()
    a.unlink();v.backup(a)
    link=root/'linked.sqlite'
    try:
        link.symlink_to(b)
        try:cleanup.plan([link],expected);raise AssertionError('Link accepted')
        except VaultError:assert b.exists()
    except OSError:pass # Windows symlink privilege may be unavailable
    shared=root/'wormwright-vault.sqlite';v.backup(shared);shared_review=cleanup.plan([shared],expected,[path]);lock=root/'.wormwright-sync-lock';lock.mkdir()
    try:cleanup.remove_shared(shared_review,root);raise AssertionError('Busy NAS master removed')
    except VaultError:assert shared.exists() and lock.is_dir()
    lock.rmdir();deleted,errors=cleanup.remove_shared(shared_review,root);assert not shared.exists() and not errors and not lock.exists()
    reviewed=cleanup.plan([a,b],expected,[path]);removed,failures=cleanup.remove(reviewed)
    assert set(removed)=={str(a),str(b)} and not failures and path.exists() and (root/'unrelated.sqlite').exists()
    v.lock()
    window=ManagedWindow(path);window.auto_timer.stop();window.vault.unlock('Invented-Deletion-Test-Password!');window.update_state()
    with patch.object(window,'reauthenticate',return_value=None),patch.object(window,'review_deletion') as review:
        window.delete_local_vault();assert path.exists() and not review.called
    with patch.object(window,'reauthenticate',return_value={'password':'invented'}),patch.object(window,'review_deletion',return_value=False):
        window.delete_local_vault();assert path.exists()
    settings=path.with_name(path.name+'.sync.json');settings.write_text('{}')
    with patch.object(window,'reauthenticate',return_value={'password':'invented'}),patch.object(window,'review_deletion',return_value=True):window.delete_local_vault()
    assert not path.exists() and not settings.exists() and (root/'unrelated.sqlite').exists() and not window.vault.unlocked
    window.new_vault # creation remains offered after removal
    window.close()
print('PASS cleanup identity, exclusion, link rejection, changed-file atomic precheck, authentication cancellation, final-review cancellation, local deletion and sync disconnection')
