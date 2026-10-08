"""Explicit whole-vault synchronization; conflicting edits never overwrite."""
from contextlib import closing
import hashlib
import json
import os
import shutil
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid
from nacl.secret import SecretBox
from vault import Vault, VaultError
from merge import state, decisions

class SyncConflict(VaultError):
    pass


DEFAULT_LIMIT = 10


def fingerprint(path):
    digest = hashlib.sha256()
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        for table, columns in [('metadata', 'name,value'), ('entries', 'id,payload')]:
            for row in db.execute(f'SELECT {columns} FROM {table} ORDER BY 1'):
                for value in row:
                    data = value if isinstance(value, bytes) else str(value).encode()
                    digest.update(len(data).to_bytes(8, 'big'))
                    digest.update(data)
    return digest.hexdigest()


def atomic_json(path, data):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.sync-state-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def settings_path(vault):
    return vault.path.with_name(vault.path.name + '.sync.json')


def read_settings(vault):
    path = settings_path(vault)
    return json.loads(path.read_text()) if path.exists() else {'limit': DEFAULT_LIMIT}


def configure(vault, folder, limit, automatic=True, interval=30):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise VaultError('Keep between 1 and 1000 automatic sync backups.')
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise VaultError('Mount the shared folder before configuring sync.')
    remote = folder / 'wormwright-vault.sqlite'
    if remote == vault.path.resolve():
        raise VaultError('Use a local working vault separate from the shared copy.')
    previous = read_settings(vault)
    if type(interval) is not int or not 5 <= interval <= 86400:
        raise VaultError('Choose a sync interval from 5 to 86400 seconds.')
    data = {'folder': str(folder), 'limit': limit, 'automatic': bool(automatic), 'interval': interval}
    if previous.get('folder') == str(folder):
        data['baseline'] = previous.get('baseline')
        if 'managed_baseline' in previous:
            data['managed_baseline'] = previous['managed_baseline']
        if previous.get('entry_history'):
            data['entry_history'] = previous['entry_history']
    atomic_json(settings_path(vault), data)


def backup(vault, target):
    directory = target.parent / '.wormwright-sync-backups'
    directory.mkdir(mode=0o700, exist_ok=True)
    prefix = hashlib.sha256(target.name.encode()).hexdigest()[:16] + '-'
    path = directory / (prefix + str(time.time_ns()) + '-' + uuid.uuid4().hex + '.sqlite')
    with tempfile.TemporaryDirectory(prefix="wormwright-backup-") as temporary:
        snapshot = Path(temporary) / "snapshot.sqlite"
        vault.backup(snapshot)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        shutil.copyfile(snapshot, path)
    return directory, prefix


def prune(directory, prefix, limit):
    files = sorted((p for p in directory.glob(prefix + '*.sqlite') if p.is_file() and not p.is_symlink()), key=lambda p: p.name, reverse=True)
    for path in files[limit:]:
        path.unlink()


def synchronize(vault, backup_target=None, encrypted_only=False):
    if not vault.unlocked and not encrypted_only:
        raise VaultError('Unlock the local vault before syncing.')
    config = read_settings(vault)
    if not config.get('folder'):
        raise VaultError('Choose a shared folder in Sync Settings first.')
    folder = Path(config['folder'])
    if not folder.is_dir():
        raise VaultError('The shared folder is unavailable. Mount it and try again.')
    remote = folder / 'wormwright-vault.sqlite'
    lock = folder / '.wormwright-sync-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise VaultError('Another sync is running, or an interrupted sync left a lock. No files were changed. Check the other devices before removing .wormwright-sync-lock.')
    staged = None
    other = None
    temporary = tempfile.TemporaryDirectory(prefix="wormwright-sync-")
    scratch = Path(temporary.name)
    try:
        if remote.is_symlink() or remote.resolve() == vault.path.resolve():
            raise VaultError('The shared vault must be a separate regular file.')
        for suffix in ('-wal', '-journal'):
            if Path(str(remote) + suffix).exists():
                raise VaultError('The shared vault is open or has unfinished database writes. Close it before syncing.')
        if encrypted_only:
            validate_encrypted(vault.path)
        local_hash = fingerprint(vault.path)
        snapshot = scratch / "remote.sqlite"
        if remote.exists():
            shutil.copyfile(remote, snapshot)
        if encrypted_only and snapshot.exists():
            validate_encrypted(snapshot)
        remote_hash = fingerprint(snapshot) if snapshot.exists() else None
        baseline = config.get('baseline')
        if remote_hash == local_hash:
            action = 'Already up to date.'
        elif remote_hash is None and baseline is None:
            action = 'Uploaded the first shared copy.'
        elif baseline and remote_hash == baseline:
            action = 'Uploaded local changes.'
        elif baseline and local_hash == baseline and remote_hash:
            action = 'Downloaded shared changes.'
        else:
            choices = decisions(config.get('entry_history'), state(vault.path), state(snapshot)) if baseline and remote_hash else None
            if choices is None or any(choice is None for choice in choices.values()):
                raise SyncConflict('Competing edits, authentication changes, or missing sync history need review. Nothing was overwritten. Click Sync Now to resolve the differences.')
            action = 'Merged independent entry changes.'
        if remote_hash and remote_hash != local_hash:
            # Validate that this is the same encrypted vault, not another vault.
            other = EncryptedSnapshot(snapshot) if encrypted_only else Vault(snapshot)
            other.db = sqlite3.connect(snapshot.resolve().as_uri() + '?mode=ro', uri=True)
            if not encrypted_only:
                other.box = SecretBox(vault.data_key)
                records = other.entries()
                if not records:
                    ours = dict(vault.db.execute('SELECT name,value FROM metadata'))
                    theirs = dict(other.db.execute('SELECT name,value FROM metadata'))
                    if ours.get('wrapped_key') != theirs.get('wrapped_key'):
                        raise VaultError('Cannot confirm that an empty shared copy belongs to this vault. Nothing was overwritten.')
        retained = []
        if action.startswith('Merged'):
            retained.append(backup(other, remote))
            retained.append(backup(vault, backup_target or vault.path))
            merged_path = scratch / 'merged.sqlite'
            vault.backup(merged_path)
            ours = dict(vault.db.execute('SELECT id,payload FROM entries'))
            theirs = dict(other.db.execute('SELECT id,payload FROM entries'))
            with closing(sqlite3.connect(merged_path)) as db:
                with db:
                    db.execute('DELETE FROM entries')
                    db.executemany('INSERT INTO entries VALUES (?,?)',
                        [(key, records[key]) for key, choice in choices.items()
                         for records in [ours if choice == 'local' else theirs] if key in records])
            validate_encrypted(merged_path)
            if not encrypted_only:
                check = Vault(merged_path)
                try:
                    check.reopen_unlocked(vault.data_key)
                finally:
                    check.lock()
            new_hash = fingerprint(merged_path)
            fd, name = tempfile.mkstemp(dir=folder, prefix='.wormwright-sync-', suffix='.sqlite')
            os.close(fd)
            staged = Path(name)
            shutil.copyfile(merged_path, staged)
            other.lock()
            os.replace(staged, remote)
            fd, name = tempfile.mkstemp(dir=vault.path.parent, prefix='.wormwright-sync-', suffix='.sqlite')
            os.close(fd)
            staged = Path(name)
            shutil.copyfile(merged_path, staged)
            session_key = vault.data_key
            vault.lock()
            os.replace(staged, vault.path)
            if encrypted_only:
                vault.db = sqlite3.connect(vault.path)
            else:
                vault.reopen_unlocked(session_key)
        elif action.startswith('Uploaded'):
            if other:
                retained.append(backup(other, remote))
            retained.append(backup(vault, backup_target or vault.path))
            fd, name = tempfile.mkstemp(dir=folder, prefix='.wormwright-sync-', suffix='.sqlite')
            os.close(fd)
            staged = Path(name)
            staged.unlink()
            upload = scratch / "upload.sqlite"
            vault.backup(upload)
            shutil.copyfile(upload, staged)
            if other:
                other.lock()
            os.replace(staged, remote)
            new_hash = local_hash
        elif action.startswith('Downloaded'):
            retained.append(backup(vault, backup_target or vault.path))
            fd, name = tempfile.mkstemp(dir=vault.path.parent, prefix='.wormwright-sync-', suffix='.sqlite')
            os.close(fd)
            staged = Path(name)
            staged.unlink()
            other.backup(staged)
            session_key = vault.data_key
            vault.lock()
            os.replace(staged, vault.path)
            if encrypted_only:
                vault.db = sqlite3.connect(vault.path)
            else:
                vault.reopen_unlocked(session_key)
            new_hash = remote_hash
        else:
            new_hash = local_hash
        config['baseline'] = new_hash
        config['entry_history'] = state(vault.path)
        atomic_json(settings_path(vault), config)
        # Prune only this app's automatic sync backups, after a successful sync.
        for target in (backup_target or vault.path, remote):
            directory = target.parent / '.wormwright-sync-backups'
            if directory.exists():
                prune(directory, hashlib.sha256(target.name.encode()).hexdigest()[:16] + '-', config.get('limit', DEFAULT_LIMIT))
        return action
    finally:
        if other:
            other.lock()
        if staged:
            staged.unlink(missing_ok=True)
        temporary.cleanup()
        lock.rmdir()


def validate_encrypted(path):
    """Check the SQLite envelope; authenticated contents are checked on unlock."""
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise VaultError('The encrypted vault file is damaged.')
        metadata = dict(db.execute('SELECT name,value FROM metadata'))
        if metadata.get('version') != b'1' or not isinstance(metadata.get('salt'), bytes) or len(metadata['salt']) != 16 or not isinstance(metadata.get('wrapped_key'), bytes) or len(metadata['wrapped_key']) != 72:
            raise VaultError('This is not a supported encrypted vault.')
        for identity, payload in db.execute('SELECT id,payload FROM entries'):
            if not isinstance(identity, str) or not isinstance(payload, bytes) or len(payload) < 40:
                raise VaultError('An encrypted entry has an invalid envelope.')


class EncryptedSnapshot(Vault):
    """SQLite copying only; carries no data key or plaintext entry access."""
    def backup(self, destination):
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(destination)) as target:
                self.db.backup(target)
        except Exception:
            Path(destination).unlink(missing_ok=True)
            raise
