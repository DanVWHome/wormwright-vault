"""Background network work on encrypted snapshots, never the UI connection."""
from pathlib import Path
import tempfile
import sqlite3
from contextlib import closing
from PySide6.QtCore import QThread
from sync import synchronize, settings_path, atomic_json, fingerprint, SyncConflict, EncryptedSnapshot
from vault import Vault

class AutoSyncTask(QThread):
    def __init__(self, vault, settings, parent=None):
        super().__init__(parent)
        self.original = vault.path.resolve()
        self.settings = dict(settings)
        self.temporary = tempfile.TemporaryDirectory(prefix='wormwright-auto-')
        self.snapshot = Path(self.temporary.name) / 'working.sqlite'
        try:
            if vault.unlocked:
                vault.backup(self.snapshot)
            else:
                with closing(sqlite3.connect(vault.path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
                    with closing(sqlite3.connect(self.snapshot)) as target:
                        source.backup(target)
                self.snapshot.chmod(0o600)
            self.original_hash = fingerprint(self.snapshot)
            atomic_json(settings_path(Vault(self.snapshot)), self.settings)
        except Exception:
            self.temporary.cleanup()
            raise
        self.key = vault.data_key
        self.result = None
        self.error = None
        self.conflict = False
        self.baseline = None

    def run(self):
        vault = Vault(self.snapshot) if self.key is not None else EncryptedSnapshot(self.snapshot)
        try:
            encrypted_only = self.key is None
            if encrypted_only:
                vault.db = sqlite3.connect(self.snapshot)
            else:
                vault.reopen_unlocked(self.key)
            self.result = synchronize(vault, backup_target=self.original, encrypted_only=encrypted_only)
            from sync import read_settings
            self.baseline = read_settings(vault)['baseline']
        except Exception as error:
            self.conflict = isinstance(error, SyncConflict)
            self.error = str(error)
        finally:
            vault.lock()
            self.key = None

    def cleanup(self):
        self.key = None
        self.temporary.cleanup()


def finish_sync(vault, task):
    """Apply a completed snapshot only if the current local copy stayed unchanged."""
    import os
    import shutil
    from sync import read_settings
    if vault.path.resolve() != task.original or read_settings(vault) != task.settings:
        raise ValueError('Vault or sync settings changed during background sync. Retry sync.')
    if task.error:
        raise ValueError(task.error)
    changed = fingerprint(vault.path) != task.original_hash
    if task.result.startswith('Downloaded'):
        if changed:
            raise SyncConflict('Local entries changed while downloading. Both copies were kept. Click Sync Now to review.')
        fd, name = tempfile.mkstemp(dir=vault.path.parent, prefix='.auto-download-', suffix='.sqlite')
        os.close(fd)
        staged = Path(name)
        session_key = vault.data_key
        if session_key is not None:
            candidate = Vault(task.snapshot)
            try:
                candidate.reopen_unlocked(session_key)
            finally:
                candidate.lock()
        try:
            shutil.copyfile(task.snapshot, staged)
            vault.lock()
            os.replace(staged, vault.path)
            if session_key is not None:
                vault.reopen_unlocked(session_key)
        finally:
            staged.unlink(missing_ok=True)
    settings = dict(task.settings)
    settings['baseline'] = task.baseline
    atomic_json(settings_path(vault), settings)
    return changed
