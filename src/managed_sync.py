"""Snapshot sync for format 2. Administrative state never merges piecemeal."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
import uuid
from managed_vault import ManagedVault, AccountUnavailable, pack, verify
from vault import VaultError
from sync import read_settings, atomic_json, settings_path, SyncConflict

TABLES = {'metadata': 'name,value', 'users': 'id,login,salt,credential,recovery,directory,hardware',
          'groups': 'id,payload', 'exclusions': 'id,payload', 'entries': 'id,payload'}


def snapshot(source, destination):
    with closing(sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro', uri=True)) as db:
        with closing(sqlite3.connect(destination)) as target:
            db.backup(target)


def state(path):
    hashes = {}
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        meta = dict(db.execute('SELECT name,value FROM metadata'))
        if meta.get('version') != b'2':
            raise VaultError('Update all devices before using a managed-format vault.')
        # Validate management signature while locked, without decrypting identities.
        check = ManagedVault(path)
        check.db = db; check.meta = meta
        check._check_authority()
        check.db = None
        for table,columns in TABLES.items():
            rows = list(db.execute(f'SELECT {columns} FROM {table} ORDER BY 1'))
            hashes[table] = {str(row[0]): hashlib.sha256(pack([
                {'bytes': __import__('base64').b64encode(v).decode()} if isinstance(v,bytes) else v
                for v in row[1:]])).hexdigest() for row in rows}
        return {'identity': [meta['vault_id'].decode(),meta['verify'].decode()],
                'admin': hashlib.sha256(pack({k:v for k,v in hashes.items() if k!='entries'})).hexdigest(),
                'entries': hashes['entries']}


def combined(base, local, remote):
    if local['identity'] != remote['identity']:
        raise VaultError('The shared copy belongs to a different vault.')
    if local['admin'] != remote['admin']:
        return None
    if not base:
        return {eid:None for eid in set(local['entries'])|set(remote['entries'])}
    choices={}
    for eid in set(base['entries'])|set(local['entries'])|set(remote['entries']):
        old=base['entries'].get(eid);ours=local['entries'].get(eid);theirs=remote['entries'].get(eid)
        choices[eid] = 'local' if ours==theirs or theirs==old else 'shared' if ours==old else None
    return choices


def _retained(source, target, limit):
    folder=target.parent/'.wormwright-managed-backups';folder.mkdir(mode=0o700,exist_ok=True)
    prefix=hashlib.sha256(target.name.encode()).hexdigest()[:16]+'-'
    name=folder/(prefix+str(time.time_ns())+'-'+uuid.uuid4().hex+'.sqlite')
    shutil.copyfile(source,name);name.chmod(0o600)
    return folder,prefix,limit


def _replace(source, target):
    # Transfer to a temporary file on the destination mount, then rename.
    fd,name=tempfile.mkstemp(prefix='.wormwright-managed-',suffix='.sqlite',dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source,name)
        with open(name,'rb') as stream:os.fsync(stream.fileno())
        os.replace(name,target)
    finally:
        Path(name).unlink(missing_ok=True)


def synchronize(path, session=None, choices=None, expected=None):
    path=Path(path)
    config=read_settings(type('Location',(),{'path':path})())
    if not config.get('folder'):
        raise VaultError('Choose a shared folder first.')
    folder=Path(config['folder'])
    if not folder.is_dir():raise VaultError('The shared folder is unavailable.')
    remote=folder/'wormwright-vault.sqlite'
    if remote.resolve()==path.resolve() or remote.is_symlink():
        raise VaultError('Keep a separate local working vault.')
    lock=folder/'.wormwright-sync-lock'
    try:lock.mkdir()
    except FileExistsError:raise VaultError('Another sync is running or left a lock; nothing was changed.')
    retained=[]
    try:
        for suffix in ('-wal','-journal'):
            if Path(str(remote)+suffix).exists():raise VaultError('Close the shared database before syncing.')
        with tempfile.TemporaryDirectory(prefix='wormwright-managed-sync-') as root:
            local=Path(root)/'local.sqlite';shared=Path(root)/'shared.sqlite';result=Path(root)/'result.sqlite'
            snapshot(path,local);ours=state(local)
            theirs=None
            if remote.exists():
                shutil.copyfile(remote,shared);theirs=state(shared)
                if theirs['identity']!=ours['identity']:raise VaultError('The shared copy belongs to a different vault.')
            base=config.get('managed_baseline')
            if expected and expected!=[ours,theirs]:raise SyncConflict('A copy changed during review. Compare again.')
            if ours==theirs:
                message='Already up to date.';shutil.copyfile(local,result)
            elif theirs is None and base is None:
                message='Uploaded the first managed copy.';shutil.copyfile(local,result)
            elif base and ours==base:
                message='Downloaded shared changes.';shutil.copyfile(shared,result)
            elif base and theirs==base:
                message='Uploaded local changes.';shutil.copyfile(local,result)
            else:
                decisions=combined(base,ours,theirs) if theirs else None
                if decisions is None:raise SyncConflict('Account/group changes or unpaired copies need Manager review. Neither copy was overwritten.')
                if choices is not None:
                    if set(choices)!=set(decisions) or any(v not in ('local','shared') for v in choices.values()):
                        raise VaultError('Choose a side for every entry.')
                    # Ordinary users may resolve only conflicts they can see on
                    # both sides. Independent entries retain automatic decisions.
                    if not session:raise VaultError('Unlock before resolving conflicts.')
                    a=ManagedVault(local);b=ManagedVault(shared)
                    try:
                        a.resume(session);b.resume(session)
                        for eid,default in decisions.items():
                            if default is not None and choices[eid]!=default and not a.manager:
                                raise VaultError('Independent entry changes must be retained.')
                            if default is None and not a.manager:
                                a._record(eid);b._record(eid)
                    finally:a.lock();b.lock()
                    decisions=choices
                if any(value is None for value in decisions.values()):
                    raise SyncConflict('Competing entry edits need review. Neither copy was overwritten.')
                shutil.copyfile(local,result)
                with closing(sqlite3.connect(local)) as a,closing(sqlite3.connect(shared)) as b,closing(sqlite3.connect(result)) as out:
                    tables={'local':dict(a.execute('SELECT id,payload FROM entries')),'shared':dict(b.execute('SELECT id,payload FROM entries'))}
                    with out:
                        out.execute('DELETE FROM entries')
                        out.executemany('INSERT INTO entries VALUES (?,?)',[(eid,tables[side][eid]) for eid,side in decisions.items() if eid in tables[side]])
                message='Merged independent entry changes.'
            result_state=state(result)
            if session:
                check=ManagedVault(result)
                try:check.resume(session)
                except AccountUnavailable:
                    # Adopt an authenticated revocation, then the UI locks the
                    # account when it tries to resume. Do not keep stale policy.
                    pass
                finally:check.lock()
            # Recheck local edits before any publication; background callers
            # never overwrite edits made while the snapshot was in transit.
            if state(path)!=ours:raise SyncConflict('Local changes arrived during sync. Retry; neither copy was overwritten.')
            if theirs!=result_state:
                if theirs:retained.append(_retained(shared,remote,config.get('limit',10)))
                _replace(result,remote)
            if ours!=result_state:
                retained.append(_retained(local,path,config.get('limit',10)))
                # Race after remote publication is preserved rather than lost.
                if state(path)!=ours:raise SyncConflict('Local changes arrived after upload. Shared copy saved; local copy preserved. Retry.')
                _replace(result,path)
            config['managed_baseline']=result_state
            atomic_json(settings_path(type('Location',(),{'path':path})()),config)
            for directory,prefix,limit in retained:
                for old in sorted(directory.glob(prefix+'*.sqlite'),key=lambda p:p.name,reverse=True)[limit:]:
                    if old.is_file() and not old.is_symlink():old.unlink()
            return message
    finally:
        lock.rmdir()


def reconcile(path, session, authority_side, choices, expected, assignments=None):
    """Manager-only explicit reconciliation of competing administrative copies.

    All selected entries are authenticated under their original policy, then
    encrypted with fresh keys under the explicitly selected destination policy.
    No group with a missing ID is silently replaced by Generic.
    """
    if authority_side not in ('local','shared'):
        raise VaultError('Choose which copy supplies account and group settings.')
    path=Path(path);config=read_settings(type('Location',(),{'path':path})())
    folder=Path(config['folder']);remote=folder/'wormwright-vault.sqlite';lock=folder/'.wormwright-sync-lock'
    try:lock.mkdir()
    except FileExistsError:raise VaultError('Another sync is running. Retry after it finishes.')
    try:
        with tempfile.TemporaryDirectory(prefix='wormwright-managed-review-') as root:
            root=Path(root);local=root/'local.sqlite';shared=root/'shared.sqlite';result=root/'result.sqlite'
            snapshot(path,local);shutil.copyfile(remote,shared)
            if [state(local),state(shared)]!=expected:raise SyncConflict('A copy changed during review. Compare again.')
            a=ManagedVault(local);b=ManagedVault(shared);out=ManagedVault(result)
            try:
                a.resume(session);b.resume(session)
                if not a.manager or not b.manager:raise VaultError('Only the Manager can reconcile account/group changes.')
                ours={r['id']:r for r in a.entries(True)};theirs={r['id']:r for r in b.entries(True)}
                if set(choices)!=set(ours)|set(theirs) or any(c not in ('local','shared') for c in choices.values()):
                    raise VaultError('Choose a side for every entry.')
                shutil.copyfile(local if authority_side=='local' else shared,result);out.resume(session)
                with out.db:
                    out.db.execute('DELETE FROM entries')
                    for eid,side in choices.items():
                        record=(ours if side=='local' else theirs).get(eid)
                        if record is None:continue
                        record=dict(record)
                        if assignments and eid in assignments:record['groups']=assignments[eid]
                        if not record['groups'] or any(gid not in out.available_groups() for gid in record['groups']):
                            raise VaultError('An entry’s groups do not exist in the selected settings. Explicitly assign valid groups before applying.')
                        out._assignment(record);out._write(record)
                out.entries(True)
                if state(path)!=expected[0]:raise SyncConflict('Local copy changed. Nothing was overwritten.')
                retained=[_retained(local,path,config.get('limit',10)),_retained(shared,remote,config.get('limit',10))]
                out.lock()
                _replace(result,remote)
                if state(path)!=expected[0]:raise SyncConflict('Local changes arrived after publication. Local copy preserved; review again.')
                _replace(result,path)
                config['managed_baseline']=state(result);atomic_json(settings_path(type('Location',(),{'path':path})()),config)
                for directory,prefix,limit in retained:
                    for old in sorted(directory.glob(prefix+'*.sqlite'),key=lambda p:p.name,reverse=True)[limit:]:
                        if old.is_file() and not old.is_symlink():old.unlink()
                return 'Reconciled entries and Manager-selected access settings.'
            finally:a.lock();b.lock();out.lock()
    finally:lock.rmdir()
