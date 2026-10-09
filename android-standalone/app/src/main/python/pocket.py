"""Offline adapter. Reuses the unmodified signed format-2 encryption engine.

Only ciphertext is written to disk. The random local account password is supplied
by an authenticated Android Keystore operation, optionally password-wrapped.
"""
import base64
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from nacl import pwhash, secret, utils
from managed_vault import ManagedVault, derive
from vault import VaultError

_vault = None

def lock():
    global _vault
    if _vault is not None:
        _vault.lock()
    _vault = None

def new_secret():
    return secrets.token_urlsafe(48)

def protect(value, password):
    if not password:
        return json.dumps({'version': 1, 'secret': value})
    if len(password) < 12:
        raise VaultError('Use a vault password of at least 12 characters.')
    salt = utils.random(pwhash.argon2id.SALTBYTES)
    encrypted = secret.SecretBox(derive(password, salt)).encrypt(value.encode())
    return json.dumps({'version': 1, 'salt': base64.b64encode(salt).decode(),
                       'cipher': base64.b64encode(encrypted).decode()})

def unprotect(document, password):
    try:
        data = json.loads(document)
        if data['version'] != 1:
            raise ValueError()
        if 'cipher' not in data:
            return data['secret']
        salt = base64.b64decode(data['salt'], validate=True)
        encrypted = base64.b64decode(data['cipher'], validate=True)
        return secret.SecretBox(derive(password, salt)).decrypt(encrypted).decode()
    except Exception as error:
        raise VaultError('Incorrect vault password or damaged key envelope.') from error

def create(path, local_secret, vault_name):
    global _vault
    lock()
    candidate = ManagedVault(path)
    try:
        candidate.create(local_secret, username='Owner',vault_name=vault_name)
        _vault = candidate
    except Exception:
        candidate.lock()
        raise

def unlock(path, local_secret):
    global _vault
    lock()
    candidate = ManagedVault(path)
    try:
        candidate.unlock(local_secret)
        candidate.entries(include_deleted=True)  # validate every signed entry
        _vault = candidate
        return listing('')
    except Exception:
        candidate.lock()
        raise VaultError('Vault could not be unlocked. Keep the files and restore a portable backup.')

def sample(path):
    if not Path(path).exists():
        create(path, 'SampleOnly-PocketVault-2026!', 'Invented sample vault')
        for description, username, link in [
                ('Sample email', 'demo@example.invalid', 'https://mail.example.invalid'),
                ('Sample bookshop', 'book-demo', 'https://books.example.invalid')]:
            save(json.dumps({'description': description, 'user_name': username, 'link': link,
                             'password': 'Invented-Only-Password!', 'notes': 'Invented sample. No real account.'}))
        lock()
    return unlock(path, 'SampleOnly-PocketVault-2026!')

def require():
    if _vault is None or not _vault.unlocked:
        raise VaultError('Unlock the vault first.')
    return _vault

def listing(query):
    terms = query.casefold().split()
    return json.dumps([{k: r.get(k, '') for k in ('id', 'description', 'user_name', 'link')}
        for r in require().entries() if all(t in ' '.join(str(r.get(k, ''))
        for k in ('description', 'user_name', 'link')).casefold() for t in terms)], ensure_ascii=False)

def detail(eid):
    r = require()._record(eid)
    if r.get('deleted'):
        raise VaultError('This entry is in Recently deleted.')
    return json.dumps(r, ensure_ascii=False)

def save(document):
    return require().save(json.loads(document))

def delete(eid):
    require().delete(eid)

def deleted():
    return json.dumps([{'id': r['id'], 'description': r['description']}
                      for r in require().entries(include_deleted=True) if r.get('deleted')])

def recover(eid):
    require().restore_entry(eid)

def export(path, password):
    """Copy SQLite consistently and rewrap the Owner credential only.

    IDs, signed policy, entry signatures and tombstones remain
    byte-for-byte compatible. Never change the phone's credential or policy.
    """
    if len(password) < 12:
        raise VaultError('Use an export password or recovery key of at least 12 characters.')
    source = require()
    target = Path(path)
    if target.exists():
        raise VaultError('Export staging file already exists.')
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    candidate = ManagedVault(target)
    try:
        with sqlite3.connect(target) as db:
            source.db.backup(db)
        candidate.resume(source.session())
        candidate.reset_password(candidate.uid, password)
        candidate.lock()
        candidate.unlock(password)
        candidate.entries(include_deleted=True)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        candidate.lock()

def restore(source, target, recovery_secret, local_secret):
    """Validate before committing. Caller publishes a new Android slot only after
    its key envelope is safely stored; original slot remains recoverable.
    """
    path = Path(source)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise VaultError('Backup exceeds the 64 MiB limit.')
    candidate = ManagedVault(path)
    destination = ManagedVault(target)
    try:
        candidate.unlock(recovery_secret)
        if not candidate.personal:
            raise VaultError('Use the companion app for managed NAS vaults.')
        candidate.entries(include_deleted=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(target) as db:
            candidate.db.backup(db)
        destination.resume(candidate.session())
        destination.reset_password(destination.uid, local_secret)
        destination.lock()
        destination.unlock(local_secret)
        destination.entries(include_deleted=True)
    except Exception as error:
        Path(target).unlink(missing_ok=True)
        if isinstance(error, VaultError):
            raise
        raise VaultError('Incorrect recovery secret or damaged backup. Original vault was kept.') from error
    finally:
        candidate.lock()
        destination.lock()


def vault_name():
    return require().display_name


def rename_vault(name):
    require().set_display_name(name)


def verify_deletion(path,local_secret):
    candidate=ManagedVault(path)
    try:
        candidate.unlock(local_secret)
        return candidate.display_name
    finally:candidate.lock()
