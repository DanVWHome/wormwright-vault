"""Reviewable removal of exact files; never traverses or follows symlinks."""
from pathlib import Path
from contextlib import closing
import hashlib
import sqlite3
from managed_vault import ManagedVault
from vault import VaultError


def identity(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise VaultError('Choose a regular vault file, not a link.')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        meta=dict(db.execute('SELECT name,value FROM metadata'))
        check=ManagedVault(path);check.db=db;check.meta=meta
        try:check._check_authority()
        finally:check.db=None
        return meta['vault_id'],meta['verify']


def plan(paths, expected, excluded=()):
    excluded={Path(p).resolve() for p in excluded}
    result=[]
    for path in dict.fromkeys(map(Path,paths)):
        if path.is_symlink():raise VaultError('Links cannot be deleted through vault cleanup.')
        path=path.resolve()
        if path in excluded:raise VaultError('The working or shared vault is not a backup. Use Delete Local Vault for the working file.')
        if identity(path)!=expected:raise VaultError('A selected file belongs to another vault. Nothing was deleted.')
        result.append((str(path),hashlib.sha256(path.read_bytes()).hexdigest()))
    return result


def discover(vault, folders):
    expected=(vault.meta['vault_id'],vault.meta['verify']);result=[]
    for folder in dict.fromkeys(map(Path,folders)):
        if folder.is_symlink() or not folder.is_dir():continue
        for path in folder.iterdir():
            if path.is_symlink() or not path.is_file() or path.resolve()==vault.path.resolve():continue
            try:
                if identity(path)==expected:result.append(path)
            except (OSError,sqlite3.Error,KeyError,VaultError,ValueError):continue
    return result


def remove(review, settings=()):
    # Check the entire reviewed list before removing anything. Changed or replaced
    # files require a new review, even when they still have the same vault ID.
    for name,digest in review:
        path=Path(name)
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise VaultError('A reviewed file changed. Nothing was deleted; review again.')
    failures=[];removed=[]
    for path in map(Path,settings):
        try:
            if path.is_symlink():raise OSError('Link')
            path.unlink(missing_ok=True)
        except OSError:failures.append(str(path))
    if failures:raise VaultError('Could not disconnect sync. No vault files were removed.')
    for name,_ in review:
        path=Path(name)
        try:
            path.unlink();removed.append(name)
            for suffix in ('-wal','-shm','-journal'):
                sidecar=Path(name+suffix)
                if sidecar.is_symlink():failures.append(str(sidecar))
                else:
                    try:sidecar.unlink(missing_ok=True)
                    except OSError:failures.append(str(sidecar))
        except OSError:failures.append(name)
    return removed,failures


def remove_shared(review,folder,settings=()):
    from sync_lock import release_lock
    lock=Path(folder)/'.wormwright-sync-lock'
    try:lock.mkdir()
    except FileExistsError:raise VaultError('Another NAS sync is running or left a lock. Nothing was deleted.')
    try:return remove(review,settings)
    finally:release_lock(lock)
