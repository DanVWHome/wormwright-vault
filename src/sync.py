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


def configure(vault, folder, limit):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise VaultError('Keep between 1 and 1000 automatic sync backups.')
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise VaultError('Mount the shared folder before configuring sync.')
    remote = folder / 'wormwright-vault.sqlite'
    if remote == vault.path.resolve():
        raise VaultError('Use a local working vault separate from the shared copy.')
    previous = read_settings(vault)
    data = {'folder': str(folder), 'limit': limit}
    if previous.get('folder') == str(folder):
        data['baseline'] = previous.get('baseline')
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


def synchronize(vault):
    if not vault.unlocked:
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
        local_hash = fingerprint(vault.path)
        snapshot = scratch / "remote.sqlite"
        if remote.exists():
            shutil.copyfile(remote, snapshot)
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
            raise SyncConflict('Both copies changed, or these copies have not been paired. Nothing was overwritten. Keep both copies and resolve the differences before syncing.')
        if remote_hash and remote_hash != local_hash:
            # Validate that this is the same encrypted vault, not another vault.
            other = Vault(snapshot)
            other.db = sqlite3.connect(snapshot.resolve().as_uri() + '?mode=ro', uri=True)
            other.box = SecretBox(vault.data_key)
            records = other.entries()
            if not records:
                ours = dict(vault.db.execute('SELECT name,value FROM metadata'))
                theirs = dict(other.db.execute('SELECT name,value FROM metadata'))
                if ours.get('wrapped_key') != theirs.get('wrapped_key'):
                    raise VaultError('Cannot confirm that an empty shared copy belongs to this vault. Nothing was overwritten.')
        retained = []
        if action.startswith('Uploaded'):
            if other:
                retained.append(backup(other, remote))
            retained.append(backup(vault, vault.path))
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
            retained.append(backup(vault, vault.path))
            fd, name = tempfile.mkstemp(dir=vault.path.parent, prefix='.wormwright-sync-', suffix='.sqlite')
            os.close(fd)
            staged = Path(name)
            staged.unlink()
            other.backup(staged)
            session_key = vault.data_key
            vault.lock()
            os.replace(staged, vault.path)
            vault.reopen_unlocked(session_key)
            new_hash = remote_hash
        else:
            new_hash = local_hash
        config['baseline'] = new_hash
        atomic_json(settings_path(vault), config)
        # Prune only this app's automatic sync backups, after a successful sync.
        for target in (vault.path, remote):
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
