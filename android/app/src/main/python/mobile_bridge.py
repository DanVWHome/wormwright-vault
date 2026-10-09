"""Read-only Android adapter over the unmodified Linux format-2 engine.

No password, entry or key material is persisted by this bridge. SQLite is opened
read-only and the original selected document is never mutated.
"""
import json
import hashlib
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from managed_vault import ManagedVault, AccountUnavailable
from vault import VaultError
import mobile_sync


class ReadOnlyVault(ManagedVault):
    def _connect(self):
        if not self.path.is_file():
            raise VaultError('Import an encrypted vault first.')
        self.db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)
        self.db.execute('PRAGMA query_only=ON')
        self.meta = dict(self.db.execute('SELECT name,value FROM metadata'))
        if self.meta.get('version') != b'2':
            raise VaultError('This preview supports the current Linux vault format (version 2).')
        self._check_authority()


_vault = None
_sample = False
_pending = None


def validate_file(path):
    """Check structure and signed policy before accepting an imported snapshot."""
    candidate = ReadOnlyVault(path)
    try:
        candidate._connect()
        result = {'personal': candidate.meta['mode'] == b'personal'}
        if candidate.meta['mode'] not in (b'personal', b'managed'):
            raise VaultError('Unsupported vault mode.')
        return json.dumps(result)
    finally:
        candidate.lock()


def unlock(path, username, password, editable=False, sample=False):
    global _vault, _sample
    lock()
    candidate = ManagedVault(path) if editable else ReadOnlyVault(path)
    try:
        candidate.unlock(password, username)
        _vault = candidate
        _sample = bool(sample)
        return list_entries('')
    except Exception:
        candidate.lock()
        raise


def list_entries(query):
    if _vault is None:
        raise VaultError('Unlock the vault first.')
    terms = str(query).casefold().split()
    result = []
    for record in _vault.entries():
        # Search only visible fields; password and notes never enter the list.
        searchable = ' '.join(str(record.get(k, '')) for k in ('description', 'user_name', 'link')).casefold()
        if all(term in searchable for term in terms):
            result.append({k: record.get(k, '') for k in ('id', 'description', 'user_name', 'link')})
    return json.dumps(result, ensure_ascii=False)


def detail(entry_id):
    if _vault is None:
        raise VaultError('Unlock the vault first.')
    record = _vault._record(str(entry_id))
    if record.get('deleted'):
        raise VaultError('Entry is unavailable.')
    return json.dumps({k: record.get(k, '') for k in ('id', 'description', 'user_name', 'link', 'password', 'notes', 'groups')}, ensure_ascii=False)


def lock():
    global _vault, _pending
    if _vault is not None:
        _vault.lock()
    _vault = None
    _pending = None


def editing_info():
    if not session_ready(): raise VaultError('Unlock first.')
    paired = mobile_sync.read_config(_vault.path)
    return json.dumps({'can_edit': not isinstance(_vault, ReadOnlyVault) and (_sample or Path(str(_vault.path)+'.local-only').is_file() or bool(paired and paired.get('paired'))),
                       'manager': _vault.manager, 'groups': _vault.available_groups()})


def save_entry(document):
    if not json.loads(editing_info())['can_edit']:
        raise VaultError('Complete the first NAS sync before editing this phone copy.')
    if _pending is not None: raise VaultError('Wait for sync to finish before editing.')
    record = json.loads(document)
    return _vault.save(record)


def delete_entry(entry_id):
    if not json.loads(editing_info())['can_edit']:
        raise VaultError('Complete the first NAS sync before editing.')
    if _pending is not None: raise VaultError('Wait for sync to finish before deleting.')
    _vault.delete(str(entry_id))


def prepare_sync(downloaded, local_path, result_path, endpoint, choices='', expected=''):
    global _pending
    local = Path(local_path).resolve()
    if not session_ready() or _vault.path.resolve() != local or _sample:
        raise VaultError('Unlock the phone vault before syncing.')
    try:
        plan = mobile_sync.prepare(local, downloaded, result_path, _vault.session(), str(endpoint),
                                   json.loads(choices) if choices else None, json.loads(expected) if expected else None)
    except VaultError as error:
        _pending = None
        return json.dumps({'ready': False, 'conflicts': [], 'message': str(error)})
    _pending = {'plan': plan, 'result': str(result_path), 'local': str(local)} if plan['ready'] else None
    return json.dumps(plan)


def ensure_sync_current():
    if _pending is None or not session_ready(): raise VaultError('Sync is no longer active.')
    mobile_sync.ensure_current(_pending['local'], _pending['plan'])


def commit_sync(resume=True):
    global _vault, _pending
    if _pending is None or not session_ready(): raise VaultError('Sync is no longer active.')
    pending = _pending; session = _vault.session(); _vault.lock()
    try:
        mobile_sync.commit(pending['local'], pending['result'], pending['plan'])
        if resume and not pending['plan']['revoked']:
            _vault = ManagedVault(pending['local']); _vault.resume(session)
        else: _vault = None
        return json.dumps({'message': pending['plan']['message'], 'revoked': pending['plan']['revoked']})
    except Exception:
        _vault = ManagedVault(pending['local'])
        try: _vault.resume(session)
        except Exception: _vault.lock(); _vault = None
        raise
    finally: _pending = None


def abort_sync():
    global _pending
    _pending = None


def safe_error(error):
    # Known user-facing validation errors contain no credentials or entry fields.
    if isinstance(error, VaultError): return str(error)
    return 'Sync validation failed. Your local edits are preserved.'


def import_snapshot(source, destination):
    validate_file(source)
    destination = Path(destination)
    config = mobile_sync.read_config(destination)
    if config and config.get('paired') and mobile_sync.state(destination) != config['baseline']:
        raise VaultError('Sync pending phone edits before replacing this copy. Export an encrypted backup for Manager review if needed.')
    os.replace(source, destination)
    mobile_sync.config_path(destination).unlink(missing_ok=True)
    Path(str(destination)+'.local-only').unlink(missing_ok=True)


def encrypted_backup(source, destination):
    mobile_sync.snapshot(source, destination)


def session_ready():
    return _vault is not None and _vault.unlocked


def _digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
    return digest.digest()


def apply_nas_snapshot(downloaded, local_path, guard=None):
    """Adopt a pinned, fully authenticated NAS snapshot; never publish to NAS.

    The transport has already downloaded under the desktop's shared lock. A
    failed signature, wrong identity or canceled operation leaves local intact.
    Authenticated account revocation is adopted and immediately locks the app.
    """
    global _vault
    local = Path(local_path).resolve()
    source = Path(downloaded).resolve()
    if _vault is None or not _vault.unlocked or _vault.path.resolve() != local:
        raise VaultError('Unlock your imported phone vault before refreshing from NAS.')
    session = _vault.session()
    original = _digest(local)
    candidate = ReadOnlyVault(source)
    revoked = False
    try:
        # Pin both vault ID and signing authority to the already imported copy.
        candidate._connect()
        if candidate.meta['vault_id'] != session[2] or candidate.meta['verify'] != session[3]:
            raise VaultError('The NAS copy belongs to a different vault.')
        candidate.lock()
        try:
            candidate.resume(session)
        except AccountUnavailable:
            revoked = True
        finally:
            candidate.lock()
        if guard is not None and not guard.getAsBoolean():
            raise VaultError('NAS refresh canceled because the app was locked.')
        if _digest(local) != original:
            raise VaultError('The phone copy changed during refresh. Retry.')
        if _digest(source) == original:
            return json.dumps({'message': 'Already up to date.', 'revoked': False})
        folder = local.parent / 'nas-backups'
        folder.mkdir(mode=0o700, exist_ok=True)
        fd, backup_name = tempfile.mkstemp(prefix=str(time.time_ns()) + '-', suffix='.sqlite', dir=folder)
        with os.fdopen(fd, 'wb') as destination, local.open('rb') as origin:
            shutil.copyfileobj(origin, destination)
            destination.flush()
            os.fsync(destination.fileno())
        # Close SQLite before replacement. The network file is never a DB path.
        lock()
        try:
            os.replace(source, local)
            if not revoked:
                restored = ReadOnlyVault(local)
                restored.resume(session)
                _vault = restored
        except Exception:
            if 'restored' in locals():
                restored.lock()
            # Keep a usable original if local replacement or resumption fails.
            fd, recovery = tempfile.mkstemp(prefix='nas-recovery-', suffix='.sqlite', dir=local.parent)
            os.close(fd)
            shutil.copyfile(backup_name, recovery)
            os.replace(recovery, local)
            previous = ReadOnlyVault(local)
            previous.resume(session)
            _vault = previous
            raise
        for old in sorted(folder.glob('*.sqlite'), key=lambda p: p.name, reverse=True)[10:]:
            old.unlink()
        return json.dumps({'message': 'NAS changes downloaded.' if not revoked else 'This account is no longer available. Vault locked.',
                           'revoked': revoked})
    finally:
        candidate.lock()


def create_personal(path,password):
    lock()
    path=Path(path)
    if path.exists():raise VaultError('A phone vault already exists.')
    candidate=ManagedVault(path)
    try:
        candidate.create(password,username='Owner')
        Path(str(path)+'.local-only').write_text('Independent personal phone vault\n')
    finally:candidate.lock()


def verify_deletion(path,username,password):
    candidate=ManagedVault(path)
    try:candidate.unlock(password,username);return 'Authorized'
    finally:candidate.lock()


def delete_phone_copy(path):
    lock()
    path=Path(path)
    if path.name!='vault.db':raise VaultError('Unsupported phone copy.')
    # Only app-private files in this copy's directory, never a NAS or selected document.
    failures=[]
    for item in path.parent.iterdir():
        name=item.name
        if name.startswith(('vault.db','sample.db','import-','export-','nas-settings-')) or name=='nas-settings.enc':
            try:
                if item.is_symlink() or not item.is_file():raise OSError()
                item.unlink()
            except OSError:failures.append(name)
    if failures:raise VaultError('Some private phone files could not be removed.')
