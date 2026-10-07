"""Local encrypted snapshots for explicit two-way conflict resolution."""
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
from nacl.secret import SecretBox
from sync import fingerprint, read_settings, atomic_json
from vault import Vault, VaultError
from merge import state, decisions

class Comparison:
    def __init__(self, local):
        self.local = local
        self.config = read_settings(local)
        self.remote = Path(self.config['folder']) / 'wormwright-vault.sqlite'
        self.temporary = tempfile.TemporaryDirectory(prefix='wormwright-compare-')
        self.root = Path(self.temporary.name)
        self.shared = Vault(self.root / 'shared.sqlite')
        self.rows = []
        self.suggestions = {}
        self.local_hash = fingerprint(local.path)
        try:
            self._check_remote()
            shutil.copyfile(self.remote, self.shared.path)
            self.remote_hash = fingerprint(self.shared.path)
        except Exception:
            self.close()
            raise

    def _check_remote(self):
        if self.remote.is_symlink() or not self.remote.is_file():
            raise VaultError('The shared vault is unavailable or is not a regular file.')
        for suffix in ('-wal', '-journal'):
            if Path(str(self.remote) + suffix).exists():
                raise VaultError('Close the shared vault before comparing or syncing.')

    def unlock_shared(self, password):
        self.shared.unlock(password)

    def compare(self):
        if not self.local.unlocked or not self.shared.unlocked:
            raise VaultError('Unlock both vaults before comparing.')
        ours = {r['id']: r for r in self.local.entries()}
        theirs = {r['id']: r for r in self.shared.entries()}
        self.rows = [(key, ours.get(key), theirs.get(key)) for key in sorted(ours.keys() | theirs.keys(), key=lambda k: (ours.get(k) or theirs[k]).get('description', '').casefold())]
        self.suggestions = decisions(self.config.get('entry_history'), state(self.local.path), state(self.shared.path)) or {}
        return self.rows

    def apply(self, choices):
        if not self.local.unlocked or not self.shared.unlocked:
            raise VaultError('The vault locked. Unlock and compare again.')
        if len(choices) != len(self.rows) or any(c not in ('local', 'shared', 'omit') for c in choices):
            raise VaultError('Choose a result for every entry.')
        selected = []
        for (_, ours, theirs), choice in zip(self.rows, choices):
            record = ours if choice == 'local' else theirs if choice == 'shared' else None
            if record is not None:
                selected.append(record)
        lock = self.remote.parent / '.wormwright-sync-lock'
        try:
            lock.mkdir()
        except FileExistsError:
            raise VaultError('Another sync is running. Try again after it finishes.')
        transfer = None
        local_stage = None
        try:
            self._check_remote()
            current = self.root / 'current.sqlite'
            shutil.copyfile(self.remote, current)
            if fingerprint(self.local.path) != self.local_hash or fingerprint(current) != self.remote_hash:
                raise VaultError('A copy changed while you were comparing. Nothing was overwritten. Compare again.')
            # Safety backups of both originals. Retention pruning never touches these.
            from time import time_ns
            token = str(time_ns())
            safety_local = self.local.path.with_name(self.local.path.name + '.conflict-' + token + '.sqlite')
            safety_shared = self.remote.with_name(self.remote.name + '.conflict-' + token + '.sqlite')
            self.local.backup(safety_local)
            fd = os.open(safety_shared, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            shutil.copyfile(self.shared.path, safety_shared)
            # Use shared encryption and unlock methods so a new device joins its vault.
            merged = Vault(self.root / 'merged.sqlite')
            self.shared.backup(merged.path)
            merged.db = sqlite3.connect(merged.path)
            merged.data_key = self.shared.data_key
            merged.box = SecretBox(merged.data_key)
            try:
                with merged.db:
                    merged.db.execute('DELETE FROM entries')
                    for record in selected:
                        merged.save(record)
                merged.entries()
            finally:
                merged.lock()
            fd, name = tempfile.mkstemp(dir=self.local.path.parent, prefix='.resolved-', suffix='.sqlite')
            os.close(fd)
            local_stage = Path(name)
            shutil.copyfile(merged.path, local_stage)
            fd, name = tempfile.mkstemp(dir=self.remote.parent, prefix='.resolved-', suffix='.sqlite')
            os.close(fd)
            transfer = Path(name)
            shutil.copyfile(merged.path, transfer)
            os.replace(transfer, self.remote)
            self.local.lock()
            os.replace(local_stage, self.local.path)
            self.local.reopen_unlocked(self.shared.data_key)
            self.config['baseline'] = fingerprint(self.local.path)
            self.config['entry_history'] = state(self.local.path)
            atomic_json(self.local.path.with_name(self.local.path.name + '.sync.json'), self.config)
            return safety_local, safety_shared
        finally:
            for path in (transfer, local_stage):
                if path:
                    path.unlink(missing_ok=True)
            lock.rmdir()

    def close(self):
        self.rows.clear()
        self.shared.lock()
        self.temporary.cleanup()
