"""Mobile transactions using the unchanged Linux state and merge decisions."""
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
from managed_vault import ManagedVault, AccountUnavailable, pack
from vault import VaultError

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


def config_path(local):
    return Path(str(local) + '.mobile-sync.json')


def read_config(local):
    path = config_path(local)
    return json.loads(path.read_text()) if path.exists() else None


def write_config(local, value):
    path = config_path(local)
    fd, name = tempfile.mkstemp(prefix='sync-state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def authenticated(path, session):
    check = ManagedVault(path)
    try:
        check.resume(session)
        return False
    except AccountUnavailable:
        return True
    finally:
        check.lock()


def prepare(local, remote, result, session, endpoint, choices=None, expected=None):
    """Prepare only. Publication and phone commit happen later under NAS lock."""
    local, remote, result = map(Path, (local, remote, result))
    ours, theirs = state(local), state(remote)
    if ours['identity'] != theirs['identity']:
        raise VaultError('The NAS copy belongs to a different vault.')
    if expected is not None and [ours, theirs] != expected:
        raise VaultError('A copy changed during conflict review. Sync again to review the latest copies.')
    revoked = authenticated(remote, session)
    config = read_config(local)
    base = config['baseline'] if config and config.get('paired') else None
    if config and config.get('endpoint') != endpoint:
        if ours != base:
            raise VaultError('Sync pending phone edits to the original NAS location before changing it.')
        base = None
    if revoked:
        shutil.copyfile(remote, result)
        message = 'Account revoked. Vault locked; any phone edits are retained in an encrypted backup.'
    elif base is None:
        # Upgrade from a read-only preview: first pair before allowing edits.
        shutil.copyfile(remote, result)
        message = 'Paired with NAS. Phone editing is ready.'
    elif ours == theirs:
        shutil.copyfile(local, result); message = 'Already up to date.'
    elif ours == base:
        shutil.copyfile(remote, result); message = 'NAS changes downloaded.'
    elif theirs == base:
        shutil.copyfile(local, result); message = 'Phone changes uploaded.'
    else:
        decisions = combined(base, ours, theirs)
        if decisions is None:
            raise VaultError('Phone edits and NAS account/group changes need Manager review. Both copies are preserved; export the encrypted phone backup for review on Linux.')
        conflicts = [eid for eid, side in decisions.items() if side is None]
        if conflicts and choices is None:
            a, b = ManagedVault(local), ManagedVault(remote)
            try:
                a.resume(session); b.resume(session)
                review = []
                for eid in sorted(conflicts):
                    left = a._record(eid); right = b._record(eid)
                    if left is None or right is None:
                        raise VaultError('An inaccessible conflict needs Manager review on Linux. Export the encrypted phone backup.')
                    review.append({'id': eid, 'phone': left['description'], 'nas': right['description'],
                                   'phone_deleted': left.get('deleted', False), 'nas_deleted': right.get('deleted', False)})
                return {'ready': False, 'conflicts': review, 'expected': [ours, theirs],
                        'message': 'The same entries changed on phone and NAS. Choose which version to keep.'}
            finally: a.lock(); b.lock()
        if conflicts:
            if set(choices) != set(conflicts) or any(side not in ('local','shared') for side in choices.values()):
                raise VaultError('Choose phone or NAS for each conflicting entry.')
            a, b = ManagedVault(local), ManagedVault(remote)
            try:
                a.resume(session); b.resume(session)
                for eid in conflicts:
                    if not a.manager:
                        if a._record(eid) is None or b._record(eid) is None:
                            raise VaultError('Only the Manager may resolve inaccessible entries.')
                    decisions[eid] = choices[eid]
            finally: a.lock(); b.lock()
        shutil.copyfile(local, result)
        with closing(sqlite3.connect(local)) as a, closing(sqlite3.connect(remote)) as b, closing(sqlite3.connect(result)) as out:
            tables = {'local': dict(a.execute('SELECT id,payload FROM entries')), 'shared': dict(b.execute('SELECT id,payload FROM entries'))}
            with out:
                out.execute('DELETE FROM entries')
                out.executemany('INSERT INTO entries VALUES (?,?)', [(eid,tables[side][eid]) for eid,side in decisions.items() if eid in tables[side]])
        message = 'Phone and NAS changes merged.'
    new_state = state(result)
    revoked = authenticated(result, session)
    if result.stat().st_size > 64 * 1024 * 1024:
        raise VaultError('The merged vault exceeds the 64 MB preview limit.')
    return {'ready': True, 'upload': theirs != new_state, 'replace_local': ours != new_state,
            'revoked': revoked, 'expected': [ours,theirs], 'baseline': new_state,
            'endpoint': endpoint, 'message': message}


def ensure_current(local, plan):
    if state(local) != plan['expected'][0]:
        raise VaultError('Phone changes arrived during sync. Retry; no phone edits were overwritten.')


def commit(local, result, plan):
    """Call only after any NAS publication was acknowledged."""
    local, result = Path(local), Path(result)
    ensure_current(local, plan)
    if state(result) != plan['baseline']:
        raise VaultError('The prepared sync result changed. Retry.')
    if plan['replace_local']:
        folder = local.parent / 'nas-backups'; folder.mkdir(mode=0o700, exist_ok=True)
        backup = folder / (str(time.time_ns()) + '-' + uuid.uuid4().hex + '.sqlite')
        snapshot(local, backup)
        fd, temporary = tempfile.mkstemp(prefix='sync-commit-', suffix='.sqlite', dir=local.parent)
        try:
            with os.fdopen(fd, 'wb') as stream, result.open('rb') as origin:
                shutil.copyfileobj(origin, stream); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, local)
        finally: Path(temporary).unlink(missing_ok=True)
        for old in sorted(folder.glob('*.sqlite'), key=lambda p:p.name, reverse=True)[10:]: old.unlink()
    # Upload failure must never reach this line: old baseline remains for retry.
    write_config(local, {'paired': True, 'baseline': plan['baseline'], 'endpoint': plan['endpoint']})
