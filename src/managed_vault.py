"""Format 2: per-user credentials, signed policy, per-entry key envelopes.

Opaque identities and ciphertext lengths remain observable. Offline snapshots
cannot provide immediate revocation or rollback protection.
"""
import base64
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import shutil
import tempfile
import uuid
from nacl import pwhash, secret, utils
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey, VerifyKey
from vault import VaultError


class AccountUnavailable(VaultError):
    pass


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def b64(value):
    return base64.b64encode(bytes(value)).decode()


def un64(value):
    return base64.b64decode(value, validate=True)


def identifier():
    return str(uuid.uuid4())


def sign(key, data):
    return {'data': data, 'signature': b64(key.sign(pack(data)).signature)}


def verify(key, document):
    VerifyKey(un64(key)).verify(pack(document['data']), un64(document['signature']))
    return document['data']


def derive(password, salt):
    return pwhash.argon2id.kdf(32, password.encode(), salt,
        opslimit=pwhash.argon2id.OPSLIMIT_MODERATE, memlimit=pwhash.argon2id.MEMLIMIT_MODERATE)


def is_managed(path):
    if not Path(path).is_file():
        return False
    try:
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
            return db.execute("SELECT value FROM metadata WHERE name='version'").fetchone() == (b'2',)
    except sqlite3.Error:
        return False


class ManagedVault:
    def __init__(self, path):
        self.path = Path(path)
        self.db = None
        self.material = None
        self.cap = None
        self.uid = None
        self.meta = None

    @property
    def unlocked(self):
        return self.material is not None

    @property
    def manager(self):
        return self.unlocked and self.uid == self.meta['manager'].decode()

    @property
    def personal(self):
        if self.db:
            return self.meta['mode'] == b'personal'
        if not self.path.exists():
            return True
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            return db.execute("SELECT value FROM metadata WHERE name='mode'").fetchone() == (b'personal',)

    def _connect(self):
        if not self.path.is_file():
            raise VaultError('Vault file does not exist.')
        self.db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True)
        self.meta = dict(self.db.execute('SELECT name,value FROM metadata'))
        if self.meta.get('version') != b'2':
            raise VaultError('This is not a managed-format vault.')
        self._check_authority()

    def _login(self, name):
        return hashlib.sha256(self.meta['vault_id'] + b'\0' + name.strip().casefold().encode()).hexdigest()

    def _admin_box(self):
        if not self.manager:
            raise VaultError('Only the Manager can manage access.')
        return secret.SecretBox(un64(self.material['admin']))

    def _signer(self):
        return SigningKey(un64(self.material['sign']))

    def _public(self, material):
        return {'box': b64(PrivateKey(un64(material['box'])).public_key),
                'sign': b64(SigningKey(un64(material['sign'])).verify_key)}

    def _new_material(self):
        return {'box': b64(PrivateKey.generate()), 'sign': b64(SigningKey.generate())}

    def _encode(self, value):
        return bytes(self._admin_box().encrypt(pack(value)))

    def _decode(self, value):
        return json.loads(self._admin_box().decrypt(value))

    def create(self, password, username='Manager', managed=False):
        if len(password) < 12:
            raise VaultError('Use an initial master password of at least 12 characters.')
        if not username.strip():
            raise VaultError('Enter a Manager username.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            self.db = sqlite3.connect(self.path)
            self.db.executescript('''CREATE TABLE metadata(name TEXT PRIMARY KEY,value BLOB NOT NULL);
                CREATE TABLE users(id TEXT PRIMARY KEY,login TEXT UNIQUE NOT NULL,salt BLOB NOT NULL,credential BLOB NOT NULL,recovery BLOB NOT NULL,directory BLOB NOT NULL,hardware BLOB);
                CREATE TABLE groups(id TEXT PRIMARY KEY,payload BLOB NOT NULL);
                CREATE TABLE exclusions(id TEXT PRIMARY KEY,payload BLOB NOT NULL);
                CREATE TABLE entries(id TEXT PRIMARY KEY,payload BLOB NOT NULL);''')
            self.uid = identifier()
            self.material = self._new_material()
            self.material['admin'] = b64(utils.random(32))
            self.meta = {'version': b'2', 'vault_id': identifier().encode(), 'manager': self.uid.encode(),
                         'mode': b'managed' if managed else b'personal',
                         'verify': self._public(self.material)['sign'].encode()}
            with self.db:
                self.db.executemany('INSERT INTO metadata VALUES (?,?)', self.meta.items())
                gid = identifier()
                self.db.execute('INSERT INTO groups VALUES (?,?)',
                    (gid, self._encode({'id': gid, 'name': 'Generic', 'members': [self.uid]})))
                self._insert_user(self.uid, username.strip(), password, self.material)
                self._publish()
            self._refresh_cap()
        except Exception:
            self.lock()
            self.path.unlink(missing_ok=True)
            raise

    def _insert_user(self, uid, name, password, material):
        if not password:
            raise VaultError('The account password cannot be empty.')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        identity = {'id': uid, 'name': name, 'disabled': False, **self._public(material)}
        recovery = self._encode({'identity': identity, 'material': material})
        credential = bytes(secret.SecretBox(derive(password, salt)).encrypt(pack(material)))
        self.db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,NULL)',
            (uid, self._login(name), salt, credential, recovery, b''))

    def administration(self):
        box = self._admin_box()
        users = {}
        for uid, recovery in self.db.execute('SELECT id,recovery FROM users'):
            data = json.loads(box.decrypt(recovery))
            if data['identity']['id'] != uid:
                raise VaultError('Account identity check failed.')
            users[uid] = data
        groups = {gid: self._decode(payload) for gid, payload in self.db.execute('SELECT id,payload FROM groups')}
        manager_id = self.meta['manager'].decode()
        for group in groups.values():
            group['members'] = list(dict.fromkeys(group['members'] + [manager_id]))
        exclusions = [self._decode(payload) for _, payload in self.db.execute('SELECT id,payload FROM exclusions')]
        return {'users': users, 'groups': groups, 'exclusions': exclusions}

    def _authority_hash(self):
        digest = hashlib.sha256()
        for key in ('version', 'vault_id', 'manager', 'mode', 'verify'):
            digest.update(pack([key, b64(self.meta[key])]))
        # Credential and hardware changes authenticate by decrypting to the
        # private keys bound by the Manager-signed directory. Policy is signed.
        for table, columns in [('users', 'id,login,recovery,directory'), ('groups', 'id,payload'), ('exclusions', 'id,payload')]:
            for row in self.db.execute(f'SELECT {columns} FROM {table} ORDER BY id'):
                digest.update(pack([b64(x) if isinstance(x, bytes) else x for x in row]))
        return digest.hexdigest()

    def _check_authority(self):
        document = json.loads(self.meta['authority'])
        data = verify(self.meta['verify'].decode(), document)
        if data != {'vault': self.meta['vault_id'].decode(), 'hash': self._authority_hash()}:
            raise VaultError('The vault access policy was changed or damaged.')

    def _publish(self):
        admin = self.administration()
        for gid, group in admin['groups'].items():
            self.db.execute('UPDATE groups SET payload=? WHERE id=?', (self._encode(group), gid))
        graph = {uid: {k: data['identity'][k] for k in ('id', 'box', 'sign', 'disabled')}
                 for uid, data in admin['users'].items()}
        groups = {gid: group['members'] for gid, group in admin['groups'].items()}
        excluded = {}
        for rule in admin['exclusions']:
            excluded.setdefault(rule['entry'], []).append(rule['user'])
        for uid, data in admin['users'].items():
            labels = {gid: group['name'] for gid, group in admin['groups'].items()
                      if uid in group['members'] or uid == self.meta['manager'].decode()}
            cap = {'vault': self.meta['vault_id'].decode(), 'user': uid, 'graph': graph,
                   'groups': groups, 'labels': labels, 'excluded': excluded}
            directory = SealedBox(PublicKey(un64(graph[uid]['box']))).encrypt(pack(sign(self._signer(), cap)))
            self.db.execute('UPDATE users SET directory=? WHERE id=?', (directory, uid))
        authority = pack(sign(self._signer(), {'vault': self.meta['vault_id'].decode(), 'hash': self._authority_hash()}))
        self.db.execute("INSERT INTO metadata VALUES ('authority',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (authority,))
        self.meta['authority'] = authority

    def _refresh_cap(self):
        self.meta = dict(self.db.execute('SELECT name,value FROM metadata'))
        self._check_authority()
        row = self.db.execute('SELECT directory FROM users WHERE id=?', (self.uid,)).fetchone()
        if not row:
            raise VaultError('This account is not available.')
        directory = json.loads(SealedBox(PrivateKey(un64(self.material['box']))).decrypt(row[0]))
        self.cap = verify(self.meta['verify'].decode(), directory)
        identity = self.cap['graph'].get(self.uid)
        if self.cap['vault'] != self.meta['vault_id'].decode() or self.cap['user'] != self.uid or not identity:
            raise VaultError('This account’s policy is invalid.')
        if identity['disabled']:
            raise AccountUnavailable('This account is disabled.')
        if any(identity[key] != value for key, value in self._public(self.material).items()):
            raise VaultError('Account keys do not match the access policy.')

    def unlock(self, password, username=''):
        self.lock()
        try:
            self._connect()
            if self.meta['mode'] == b'personal':
                row = self.db.execute('SELECT id,salt,credential FROM users WHERE id=?', (self.meta['manager'].decode(),)).fetchone()
            else:
                row = self.db.execute('SELECT id,salt,credential FROM users WHERE login=?', (self._login(username),)).fetchone()
            if not row:
                raise VaultError('Incorrect username/password or unavailable account.')
            self.uid = row[0]
            self.material = json.loads(secret.SecretBox(derive(password, row[1])).decrypt(row[2]))
            self._refresh_cap()
            self.entries(include_deleted=self.manager)
        except Exception as error:
            self.lock()
            if isinstance(error, VaultError):
                raise
            raise VaultError('Cannot unlock: incorrect credentials or damaged vault.') from error

    def verify_password(self, password):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        salt, credential = self.db.execute('SELECT salt,credential FROM users WHERE id=?', (self.uid,)).fetchone()
        try:
            material = json.loads(secret.SecretBox(derive(password, salt)).decrypt(credential))
            if not hmac.compare_digest(pack(material), pack(self.material)):
                raise ValueError('Mismatch')
        except Exception as error:
            raise VaultError('Incorrect account password.') from error

    def available_groups(self):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        return dict(self.cap['labels'])

    def _recipients(self, record):
        if record.get('deleted'):
            return {self.meta['manager'].decode()}
        members = {uid for gid in record['groups'] for uid in self.cap['groups'].get(gid, [])}
        members.add(record['creator'])
        members -= set(self.cap['excluded'].get(record['id'], []))
        members.add(self.meta['manager'].decode())
        return {uid for uid in members if uid in self.cap['graph'] and not self.cap['graph'][uid]['disabled']}

    def _read(self, eid, payload):
        envelope = json.loads(payload)
        if self.uid not in envelope['keys']:
            if self.manager:
                raise VaultError('An entry is missing its Manager key envelope.')
            return None
        data = verify(self.cap['graph'][envelope['author']]['sign'], envelope['signed'])
        if data != {k: envelope[k] for k in ('vault', 'id', 'author', 'ciphertext', 'keys')} or data['id'] != eid or data['vault'] != self.meta['vault_id'].decode():
            raise VaultError('Entry signature or identity check failed.')
        key = SealedBox(PrivateKey(un64(self.material['box']))).decrypt(un64(envelope['keys'][self.uid]))
        record = json.loads(secret.SecretBox(key).decrypt(un64(envelope['ciphertext'])))
        if record['id'] != eid:
            raise VaultError('Entry identity check failed.')
        assignment = record['assignment']
        author = assignment['data']['author']
        policy = verify(self.cap['graph'][author]['sign'], assignment)
        if policy['vault'] != data['vault'] or policy['id'] != eid or policy['creator'] != record['creator'] or policy['groups'] != record['groups']:
            raise VaultError('Entry group assignment check failed.')
        if author != self.meta['manager'].decode() and (author != record['creator'] or
                any(author not in self.cap['groups'].get(gid, []) for gid in record['groups'])):
            raise VaultError('Entry group assignment was not authorized.')
        recipients = self._recipients(record)
        if set(envelope['keys']) != recipients or self.uid not in recipients:
            raise VaultError('Entry key recipients do not match the access policy.')
        writer = envelope['author']
        if not self._can_write(record, writer):
            raise VaultError('Entry update was not authorized.')
        return record

    def _can_write(self, record, uid):
        if uid == self.meta['manager'].decode():
            return True
        if uid in self.cap['excluded'].get(record['id'], []) or self.cap['graph'][uid]['disabled']:
            return False
        return uid == record['creator'] or any(uid in self.cap['groups'].get(gid, []) for gid in record['groups'])

    def entries(self, include_deleted=False):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        if include_deleted and not self.manager:
            raise VaultError('Only the Manager can view deleted entries.')
        self._refresh_cap()
        records = []
        for eid, payload in self.db.execute('SELECT id,payload FROM entries'):
            record = self._read(eid, payload)
            if record is not None and (include_deleted or not record.get('deleted', False)):
                records.append(record)
        return sorted(records, key=lambda r: r['description'].casefold())

    def _record(self, eid):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        self._refresh_cap()
        row = self.db.execute('SELECT payload FROM entries WHERE id=?', (eid,)).fetchone()
        if not row:
            raise VaultError('Entry is unavailable.')
        record = self._read(eid, row[0])
        if record is None:
            raise VaultError('Entry is unavailable.')
        return record

    def _assignment(self, record):
        record['assignment'] = sign(self._signer(), {'vault': self.meta['vault_id'].decode(),
            'id': record['id'], 'author': self.uid, 'creator': record['creator'], 'groups': record['groups']})

    def _write(self, record):
        key = utils.random(32)
        envelope = {'vault': self.meta['vault_id'].decode(), 'id': record['id'], 'author': self.uid,
            'ciphertext': b64(secret.SecretBox(key).encrypt(pack(record))),
            'keys': {uid: b64(SealedBox(PublicKey(un64(self.cap['graph'][uid]['box']))).encrypt(key))
                     for uid in sorted(self._recipients(record))}}
        envelope['signed'] = sign(self._signer(), dict(envelope))
        self.db.execute('INSERT INTO entries VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                        (record['id'], pack(envelope)))

    def save(self, record):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        self._refresh_cap()
        incoming = dict(record)
        existing = self._record(incoming['id']) if incoming.get('id') else None
        if existing and (not self._can_write(existing, self.uid) or (existing.get('deleted') and not self.manager)):
            raise VaultError('You cannot edit this entry.')
        result = dict(existing or {'id': identifier(), 'creator': self.uid, 'deleted': False})
        for field in ('description', 'link', 'user_name', 'password', 'notes'):
            result[field] = str(incoming.get(field, ''))
        if not result['description'].strip():
            raise VaultError('A description is required.')
        if self.manager or not existing:
            result['groups'] = list(dict.fromkeys(incoming.get('groups', [gid for gid,name in self.available_groups().items() if name == 'Generic'] if self.manager else list(self.available_groups()))))
            if not result['groups'] or any(gid not in self.available_groups() for gid in result['groups']):
                raise VaultError('Choose at least one of your available groups.')
            self._assignment(result)
        elif 'groups' in incoming and incoming['groups'] != existing['groups']:
            raise VaultError('Only the Manager may change an existing entry’s groups.')
        with self.db:
            self._write(result)
        return result['id']

    def delete(self, eid):
        record = self._record(eid)
        if not self._can_write(record, self.uid):
            raise VaultError('You cannot delete this entry.')
        record['deleted'] = True
        with self.db:
            self._write(record)

    def restore_entry(self, eid):
        self._admin_box()
        record = self._record(eid)
        record['deleted'] = False
        with self.db:
            self._write(record)

    def purge(self, eid):
        self._admin_box()
        self._record(eid)
        with self.db:
            self.db.execute('DELETE FROM entries WHERE id=?', (eid,))
            for key, payload in list(self.db.execute('SELECT id,payload FROM exclusions')):
                if self._decode(payload)['entry'] == eid:
                    self.db.execute('DELETE FROM exclusions WHERE id=?', (key,))
            self._publish()
        self._refresh_cap()

    def _management_change(self, operation):
        self._admin_box()
        records = self.entries(include_deleted=True)
        with self.db:
            operation()
            self._publish()
            self._refresh_cap()
            # Re-sign assignments and rotate entry keys. Revoked recipients
            # retain old offline copies but cannot decrypt these new versions.
            for record in records:
                self._assignment(record)
                self._write(record)
        self._refresh_cap()

    def add_user(self, name, password, groups=None):
        self._admin_box()
        if not name.strip():
            raise VaultError('Enter a username.')
        admin = self.administration()
        if any(u['identity']['name'].casefold() == name.strip().casefold() for u in admin['users'].values()):
            raise VaultError('That username already exists.')
        selected = list(groups) if groups is not None else [next(gid for gid,g in admin['groups'].items() if g['name'] == 'Generic')]
        if not selected or any(gid not in admin['groups'] for gid in selected):
            raise VaultError('Select valid groups for this user.')
        uid = identifier()
        def operation():
            self._insert_user(uid, name.strip(), password, self._new_material())
            for gid in selected:
                group = dict(admin['groups'][gid])
                group['members'] = group['members'] + [uid]
                self.db.execute('UPDATE groups SET payload=? WHERE id=?', (self._encode(group), gid))
            self.db.execute("UPDATE metadata SET value=? WHERE name='mode'", (b'managed',))
            self.meta['mode'] = b'managed'
        self._management_change(operation)
        return uid

    def add_group(self, name):
        self._admin_box()
        admin = self.administration()
        if not name.strip() or any(g['name'].casefold() == name.strip().casefold() for g in admin['groups'].values()):
            raise VaultError('Enter a unique group name.')
        gid = identifier()
        def operation():
            self.db.execute('INSERT INTO groups VALUES (?,?)', (gid, self._encode({'id': gid, 'name': name.strip(), 'members': [self.meta['manager'].decode()]})))
        self._management_change(operation)
        return gid

    def set_memberships(self, uid, groups):
        admin = self.administration()
        if uid not in admin['users'] or any(g not in admin['groups'] for g in groups):
            raise VaultError('Choose an existing user and valid groups.')
        if uid == self.meta['manager'].decode() and set(groups) != set(admin['groups']):
            raise VaultError('The Manager always belongs to every group and cannot be unassigned.')
        def operation():
            for gid, group in admin['groups'].items():
                group = dict(group)
                group['members'] = [u for u in group['members'] if u != uid] + ([uid] if gid in groups else [])
                self.db.execute('UPDATE groups SET payload=? WHERE id=?', (self._encode(group), gid))
        self._management_change(operation)

    def rename_manager(self, name):
        admin = self.administration()
        name = name.strip()
        if not name:
            raise VaultError('Enter a Manager username.')
        if any(uid != self.uid and data['identity']['name'].casefold() == name.casefold()
               for uid, data in admin['users'].items()):
            raise VaultError('That username already exists.')
        data = admin['users'][self.uid]
        data['identity']['name'] = name
        def operation():
            self.db.execute('UPDATE users SET login=?,recovery=? WHERE id=?',
                            (self._login(name), self._encode(data), self.uid))
        self._management_change(operation)

    def set_excluded(self, eid, uid, excluded):
        admin = self.administration()
        if uid == self.meta['manager'].decode() or uid not in admin['users']:
            raise VaultError('Choose an ordinary user; the Manager cannot be excluded.')
        self._record(eid)
        def operation():
            for key,payload in list(self.db.execute('SELECT id,payload FROM exclusions')):
                if self._decode(payload) == {'entry': eid, 'user': uid}:
                    self.db.execute('DELETE FROM exclusions WHERE id=?', (key,))
            if excluded:
                self.db.execute('INSERT INTO exclusions VALUES (?,?)', (identifier(), self._encode({'entry': eid, 'user': uid})))
        self._management_change(operation)

    def set_disabled(self, uid, disabled):
        admin = self.administration()
        if uid == self.meta['manager'].decode() or uid not in admin['users']:
            raise VaultError('The Manager account cannot be disabled.')
        data = admin['users'][uid]
        data['identity']['disabled'] = bool(disabled)
        self._management_change(lambda: self.db.execute('UPDATE users SET recovery=? WHERE id=?', (self._encode(data), uid)))

    def emergency_lockdown(self):
        """Disable ordinary accounts and rotate entry keys in one transaction."""
        admin=self.administration()
        manager=self.meta['manager'].decode()
        users={uid:data for uid,data in admin['users'].items() if uid!=manager}
        def operation():
            for uid,data in users.items():
                data['identity']['disabled']=True
                self.db.execute('UPDATE users SET recovery=? WHERE id=?',(self._encode(data),uid))
        self._management_change(operation)
        return len(users)

    def export_database(self,destination):
        """Manager-only encrypted provision/recovery copy, without device settings."""
        self._admin_box()
        self.backup(destination)

    def reset_password(self, uid, password):
        admin = self.administration()
        if uid not in admin['users'] or not password:
            raise VaultError('Choose an account and a non-empty password.')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        wrapped = bytes(secret.SecretBox(derive(password, salt)).encrypt(pack(admin['users'][uid]['material'])))
        with self.db:
            self.db.execute('UPDATE users SET salt=?,credential=? WHERE id=?', (salt,wrapped,uid))

    def change_password(self, current_password, new_password):
        self.verify_password(current_password)
        if not new_password:
            raise VaultError('The account password cannot be empty.')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        wrapped = bytes(secret.SecretBox(derive(new_password, salt)).encrypt(pack(self.material)))
        with self.db:
            self.db.execute('UPDATE users SET salt=?,credential=? WHERE id=?', (salt,wrapped,self.uid))

    def backup(self, destination):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        destination = Path(destination)
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(destination)) as target:
                self.db.backup(target)
            with destination.open('rb') as stream:
                os.fsync(stream.fileno())
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def restore(self, source, password, username='Manager'):
        self._admin_box()
        source=Path(source).resolve()
        if source==self.path.resolve():
            raise VaultError('Choose a backup separate from the working vault.')
        session=self.session()
        fd,name=tempfile.mkstemp(prefix='.wormwright-restore-',suffix='.sqlite',dir=self.path.parent)
        os.close(fd);staged=Path(name);candidate=ManagedVault(staged)
        try:
            shutil.copyfile(source,staged)
            candidate.unlock(password,username)
            if not candidate.manager or candidate.meta['vault_id']!=session[2] or candidate.meta['verify']!=session[3]:
                raise VaultError('Restore requires a Manager-authenticated backup of this same vault.')
            restored_session=candidate.session();candidate.lock()
            safety=self.path.with_name(self.path.stem+'-before-restore-'+uuid.uuid4().hex+'.sqlite')
            self.backup(safety)
            with staged.open('rb') as stream:os.fsync(stream.fileno())
            self.lock();os.replace(staged,self.path);self.resume(restored_session)
            return safety
        finally:candidate.lock();staged.unlink(missing_ok=True)

    def session(self):
        if not self.unlocked:
            return None
        return self.uid, dict(self.material), self.meta['vault_id'], self.meta['verify']

    def resume(self, session):
        self.lock()
        try:
            self._connect()
            self.uid, self.material, identity, root = session
            if identity != self.meta['vault_id'] or root != self.meta['verify']:
                raise VaultError('The synced vault identity does not match.')
            self._refresh_cap()
            self.entries(include_deleted=self.manager)
        except Exception:
            self.lock()
            raise

    def yubikey_settings(self, username=''):
        if not self.path.is_file():
            return None
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            meta = dict(db.execute('SELECT name,value FROM metadata'))
            if self.uid:
                row = db.execute('SELECT id,hardware FROM users WHERE id=?', (self.uid,)).fetchone()
            elif meta['mode'] == b'personal':
                row = db.execute('SELECT id,hardware FROM users WHERE id=?', (meta['manager'].decode(),)).fetchone()
            else:
                login = hashlib.sha256(meta['vault_id'] + b'\0' + username.strip().casefold().encode()).hexdigest()
                row = db.execute('SELECT id,hardware FROM users WHERE login=?', (login,)).fetchone()
        if not row or row[1] is None:
            return None
        settings = json.loads(row[1])
        for field in ('credential', 'salt', 'wrapped_key'):
            settings[field] = un64(settings[field])
        settings['user'] = row[0]
        return settings

    def enroll_yubikey(self, credential, salt, response):
        from vault import Vault
        if not self.unlocked or len(salt) != 32:
            raise VaultError('Unlock the account and use a valid YubiKey salt.')
        self._refresh_cap()
        settings = {'credential': b64(credential), 'salt': b64(salt),
                    'wrapped_key': b64(secret.SecretBox(Vault._hardware_key(response)).encrypt(pack(self.material)))}
        with self.db:
            self.db.execute('UPDATE users SET hardware=? WHERE id=?', (pack(settings),self.uid))

    def unlock_yubikey(self, settings, response):
        from vault import Vault
        self.lock()
        try:
            self._connect()
            self.uid = settings['user']
            if self.yubikey_settings() != settings:
                raise VaultError('YubiKey enrollment changed. Try again.')
            self.material = json.loads(secret.SecretBox(Vault._hardware_key(response)).decrypt(settings['wrapped_key']))
            self._refresh_cap()
            self.entries(include_deleted=self.manager)
        except Exception as error:
            self.lock()
            raise VaultError('Cannot unlock this account with the YubiKey.') from error

    def verify_yubikey(self, settings, response):
        from vault import Vault
        if not self.unlocked or settings != self.yubikey_settings():
            raise VaultError('Authenticate the current account again.')
        material = secret.SecretBox(Vault._hardware_key(response)).decrypt(settings['wrapped_key'])
        if not hmac.compare_digest(material, pack(self.material)):
            raise VaultError('YubiKey authentication failed.')

    def lock(self):
        self.material = None
        self.cap = None
        self.uid = None
        self.meta = None
        if self.db:
            self.db.close()
            self.db = None


def convert_personal(source, destination, password, username='Manager', hardware_response=None):
    """Create a new format-2 copy; never replace or change the source vault."""
    from vault import Vault
    old = Vault(source)
    new = ManagedVault(destination)
    created = False
    try:
        old.unlock(password)
        records = old.entries()
        settings = old.yubikey_settings()
        if hardware_response is not None:
            old.verify_yubikey(settings, hardware_response)
        # Initial creation keeps its 12-character rule; migrated passwords may
        # already have been changed to a shorter nonempty fallback password.
        temporary_password = uuid.uuid4().hex
        new.create(temporary_password, username)
        created = True
        new.change_password(temporary_password, password)
        for record in records:
            new.save({key:record.get(key,'') for key in ('description','link','user_name','password','notes')})
        if settings and hardware_response is not None:
            new.enroll_yubikey(settings['credential'],settings['salt'],hardware_response)
        new.entries(include_deleted=True)
        return bool(settings and hardware_response is None)
    except Exception:
        new.lock()
        if created:
            Path(destination).unlink(missing_ok=True)
        raise
    finally:
        old.lock();new.lock()
