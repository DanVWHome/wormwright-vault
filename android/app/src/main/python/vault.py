"""Offline prototype storage. All entry fields are authenticated and encrypted."""
from contextlib import closing
import json
import base64
import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid
from nacl import pwhash, secret, utils
from nacl.exceptions import CryptoError


class VaultError(Exception):
    pass


class Vault:
    def __init__(self, path):
        self.path = Path(path)
        self.db = None
        self.box = None
        self.data_key = None

    @property
    def unlocked(self):
        return self.box is not None

    def create(self, password):
        if len(password) < 12:
            raise VaultError('Use a master password of at least 12 characters.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            self.db = sqlite3.connect(self.path)
            self.db.executescript('CREATE TABLE metadata (name TEXT PRIMARY KEY, value BLOB NOT NULL); CREATE TABLE entries (id TEXT PRIMARY KEY, payload BLOB NOT NULL);')
            salt = utils.random(pwhash.argon2id.SALTBYTES)
            key = self._derive(password, salt)
            data_key = utils.random(secret.SecretBox.KEY_SIZE)
            with self.db:
                self.db.executemany('INSERT INTO metadata VALUES (?,?)', [('version', b'1'), ('salt', salt), ('wrapped_key', bytes(secret.SecretBox(key).encrypt(data_key)))])
            self.box = secret.SecretBox(data_key)
            self.data_key = data_key
        except Exception:
            self.lock()
            self.path.unlink(missing_ok=True)
            raise

    def _derive(self, password, salt):
        return pwhash.argon2id.kdf(secret.SecretBox.KEY_SIZE, password.encode('utf-8'), salt,
                                  opslimit=pwhash.argon2id.OPSLIMIT_MODERATE,
                                  memlimit=pwhash.argon2id.MEMLIMIT_MODERATE)

    def unlock(self, password):
        if not self.path.is_file():
            raise VaultError('Vault file does not exist.')
        self.lock()
        try:
            self.db = sqlite3.connect(self.path)
            metadata = dict(self.db.execute('SELECT name, value FROM metadata'))
            if metadata['version'] != b'1':
                raise VaultError('Unsupported vault version.')
            key = self._derive(password, metadata['salt'])
            data_key = secret.SecretBox(key).decrypt(metadata['wrapped_key'])
            self.box = secret.SecretBox(data_key)
            self.data_key = data_key
            self.entries()  # Validate all records before displaying anything.
        except CryptoError as error:
            self.lock()
            raise VaultError('Incorrect master password or damaged vault.') from error
        except Exception as error:
            self.lock()
            if isinstance(error, VaultError):
                raise
            raise VaultError('This file is not a valid VanWormAI prototype vault.') from error

    def entries(self):
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        result = []
        for entry_id, encrypted in self.db.execute('SELECT id, payload FROM entries'):
            record = json.loads(self.box.decrypt(encrypted))
            if record['id'] != entry_id:
                raise VaultError('Entry identity check failed.')
            result.append(record)
        return sorted(result, key=lambda entry: entry['description'].casefold())

    def save(self, record):
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        record = dict(record)
        record.setdefault('id', str(uuid.uuid4()))
        if not record.get('description', '').strip():
            raise VaultError('A description is required.')
        payload = bytes(self.box.encrypt(json.dumps(record, ensure_ascii=False).encode('utf-8')))
        with self.db:
            self.db.execute('INSERT INTO entries VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (record['id'], payload))
        return record['id']

    def delete(self, entry_id):
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        with self.db:
            self.db.execute('DELETE FROM entries WHERE id=?', (entry_id,))

    def backup(self, destination):
        """Export a consistent encrypted snapshot without overwriting a file."""
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        destination = Path(destination)
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(destination)) as target:
                self.db.backup(target)
            with destination.open('rb') as snapshot:
                os.fsync(snapshot.fileno())
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def import_records(self, records):
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        existing = self.entries()
        fields = ('description', 'link', 'user_name', 'password', 'notes')
        fingerprints = {tuple(record.get(field, '') for field in fields) for record in existing}
        pending = []
        skipped = 0
        for record in records:
            fingerprint = tuple(record.get(field, '') for field in fields)
            if fingerprint in fingerprints:
                skipped += 1
                continue
            if not record.get('description', '').strip():
                raise VaultError('Every imported entry needs a description.')
            fingerprints.add(fingerprint)
            entry = {field: record.get(field, '') for field in fields}
            entry['id'] = str(uuid.uuid4())
            pending.append((entry['id'], bytes(self.box.encrypt(json.dumps(entry, ensure_ascii=False).encode()))))
        if not pending:
            return 0, skipped, None
        safety = self.path.with_name(self.path.stem + '-before-import-' + uuid.uuid4().hex[:12] + '.sqlite')
        self.backup(safety)
        with self.db:
            self.db.executemany('INSERT INTO entries VALUES (?,?)', pending)
        return len(pending), skipped, safety

    def yubikey_settings(self):
        if not self.path.is_file():
            return None
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            row = connection.execute("SELECT value FROM metadata WHERE name='yubikey'").fetchone()
        if row is None:
            return None
        settings = json.loads(row[0])
        if settings.get('version') != 1:
            raise VaultError('Unsupported YubiKey configuration.')
        for field in ('credential', 'salt', 'wrapped_key'):
            settings[field] = base64.b64decode(settings[field], validate=True)
        if len(settings['salt']) != 32:
            raise VaultError('Invalid YubiKey configuration.')
        return settings

    def verify_password(self, password):
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        metadata = dict(self.db.execute('SELECT name, value FROM metadata'))
        try:
            key = self._derive(password, metadata['salt'])
            unwrapped = secret.SecretBox(key).decrypt(metadata['wrapped_key'])
            if not hmac.compare_digest(unwrapped, self.data_key):
                raise VaultError('Incorrect fallback password.')
        except CryptoError as error:
            raise VaultError('Incorrect fallback password.') from error

    @staticmethod
    def _hardware_key(response):
        if not isinstance(response, bytes) or len(response) != 32:
            raise VaultError('The YubiKey did not return a valid unlocking secret.')
        return hashlib.sha256(b'Atlas portable YubiKey wrapping key v1\0' + response).digest()

    def enroll_yubikey(self, credential, salt, response):
        if not self.unlocked:
            raise VaultError('The vault locked during enrollment. Unlock and try again.')
        wrapping_key = self._hardware_key(response)
        if len(salt) != 32:
            raise VaultError('Invalid YubiKey salt.')
        settings = {'version': 1, 'credential': base64.b64encode(credential).decode(),
                    'salt': base64.b64encode(salt).decode(),
                    'wrapped_key': base64.b64encode(bytes(secret.SecretBox(wrapping_key).encrypt(self.data_key))).decode()}
        safety = self.path.with_name(self.path.stem + '-before-yubikey-' + uuid.uuid4().hex[:12] + '.sqlite')
        self.backup(safety)
        with self.db:
            self.db.execute("INSERT INTO metadata VALUES ('yubikey', ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (json.dumps(settings).encode(),))
        return safety

    def verify_yubikey(self, settings, response):
        """Verify a fresh assertion against the currently unlocked vault."""
        if not self.unlocked:
            raise VaultError('Unlock the vault first.')
        if self.yubikey_settings() != settings:
            raise VaultError('YubiKey settings changed. Authenticate again.')
        try:
            key = secret.SecretBox(self._hardware_key(response)).decrypt(settings['wrapped_key'])
            if not hmac.compare_digest(key, self.data_key):
                raise VaultError('YubiKey authentication failed.')
        except CryptoError as error:
            raise VaultError('YubiKey authentication failed.') from error

    def unlock_yubikey(self, settings, response):
        self.lock()
        try:
            if not self.path.is_file():
                raise VaultError('Vault file does not exist.')
            self.db = sqlite3.connect(self.path)
            # Refuse results from an enrollment that changed while waiting for touch.
            current = self.yubikey_settings()
            if current != settings:
                raise VaultError('YubiKey settings changed. Try unlocking again.')
            self.data_key = secret.SecretBox(self._hardware_key(response)).decrypt(settings['wrapped_key'])
            self.box = secret.SecretBox(self.data_key)
            self.entries()
        except Exception as error:
            self.lock()
            raise VaultError('YubiKey unlock failed. Use the fallback password if needed.') from error

    def change_password(self, current_password, new_password):
        self.verify_password(current_password)
        if not new_password:
            raise VaultError('The fallback password cannot be empty.')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        wrapping_key = self._derive(new_password, salt)
        wrapped = bytes(secret.SecretBox(wrapping_key).encrypt(self.data_key))
        safety = self.path.with_name(self.path.stem + '-before-password-change-' + uuid.uuid4().hex[:12] + '.sqlite')
        self.backup(safety)
        with self.db:
            self.db.executemany('UPDATE metadata SET value=? WHERE name=?', [(salt, 'salt'), (wrapped, 'wrapped_key')])
        return safety

    def reopen_unlocked(self, data_key):
        """Resume an already authenticated session after replacing its file."""
        self.lock()
        try:
            self.db = sqlite3.connect(self.path)
            self.data_key = data_key
            self.box = secret.SecretBox(data_key)
            self.entries()
        except Exception:
            self.lock()
            raise

    def restore(self, source, password):
        """Validate a staged snapshot, save current state, then replace atomically."""
        if not self.unlocked:
            raise VaultError('Unlock the current vault first.')
        source = Path(source).resolve()
        if source == self.path.resolve():
            raise VaultError('Choose a backup file, not the current vault.')
        fd, temporary = tempfile.mkstemp(prefix='.atlas-restore-', suffix='.sqlite', dir=self.path.parent)
        os.close(fd)
        staged = Path(temporary)
        candidate = Vault(staged)
        try:
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
                with closing(sqlite3.connect(staged)) as target:
                    original.backup(target)
            candidate.unlock(password)
            restored_key = candidate.data_key
            candidate.lock()
            with staged.open('rb') as snapshot:
                os.fsync(snapshot.fileno())
            safety = self.path.with_name(self.path.stem + '-before-restore-' + uuid.uuid4().hex[:12] + '.sqlite')
            self.backup(safety)
            self.lock()
            os.replace(staged, self.path)
            self.reopen_unlocked(restored_key)
            return safety
        finally:
            candidate.lock()
            staged.unlink(missing_ok=True)

    def lock(self):
        self.box = None
        self.data_key = None
        if self.db is not None:
            self.db.close()
            self.db = None
