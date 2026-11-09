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

    @staticmethod
    def validate_name(value):
        if not isinstance(value,str):raise VaultError('Enter a vault name.')
        value=value.strip()
        if not value or len(value)>80 or any(ord(c)<32 or ord(c)==127 for c in value):
            raise VaultError('Enter a vault name of 1–80 characters on one line.')
        return value

    @property
    def display_name(self):
        if self.meta is None:
            if not self.path.is_file():return ''
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                candidate=ManagedVault(self.path);candidate.db=db;candidate.meta=dict(db.execute('SELECT name,value FROM metadata'))
                candidate._check_authority()
                return candidate.display_name
        document=self.meta.get('display_name')
        if document is None:return ''
        try:data=verify(self.meta['verify'].decode(),json.loads(document))
        except Exception as error:raise VaultError('The vault name was changed or damaged.') from error
        if data.get('vault')!=self.meta['vault_id'].decode():
            raise VaultError('The vault name belongs to another vault.')
        return self.validate_name(data['name'])

    def set_display_name(self,value):
        if not self.unlocked or not self.manager:
            raise VaultError('Unlock the Manager account to name this vault.')
        value=self.validate_name(value)
        document=pack(sign(self._signer(),{'vault':self.meta['vault_id'].decode(),'name':value}))
        with self.db:
            self.db.execute("INSERT INTO metadata VALUES ('display_name',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",(document,))
        self.meta['display_name']=document

    def create(self, password, username='Manager', managed=False, vault_name=None):
        if vault_name is not None:vault_name=self.validate_name(vault_name)
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
            if vault_name is not None:self.set_display_name(vault_name)
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
        if 'entry_owners' in self.meta:
            digest.update(pack(['entry_owners', b64(self.meta['entry_owners'])]))
        # Credential and hardware changes authenticate by decrypting to the
        # private keys bound by the Manager-signed directory. Policy is signed.
        for table, columns in [('users', 'id,login,recovery,directory'), ('groups', 'id,payload'), ('exclusions', 'id,payload')]:
            for row in self.db.execute(f'SELECT {columns} FROM {table} ORDER BY id'):
                digest.update(pack([b64(x) if isinstance(x, bytes) else x for x in row]))
        return digest.hexdigest()

    def _check_authority(self):
        document = json.loads(self.meta['authority'])
        data = verify(self.meta['verify'].decode(), document)
        expected = {'vault': self.meta['vault_id'].decode(), 'hash': self._authority_hash()}
        if 'features' in data:
            features = data['features']
            if not isinstance(features,list) or not features or features != sorted(set(features)) or any(f not in ('view-only-users-v1','entry-ownership-v1') for f in features):
                raise VaultError('Update this app to support the vault permissions.')
            expected['features'] = features
        if data != expected:
            raise VaultError('The vault access policy was changed or damaged.')
        if 'display_name' in self.meta:self.display_name # Authenticate optional names without changing format-2 policy signatures.

    def _publish(self):
        self.meta = dict(self.db.execute('SELECT name,value FROM metadata'))
        admin = self.administration()
        # Bind legacy entry owners into Manager-signed policy before enabling
        # owner editing. New IDs bind their immutable creator in the ID itself.
        rows=list(self.db.execute('SELECT id,payload FROM entries'))
        owners=json.loads(self.meta.get('entry_owners', b'{}'))
        entry_ids={eid for eid,_ in rows}
        owners={eid:uid for eid,uid in owners.items() if eid in entry_ids}
        for eid,payload in rows:
            if ':' not in eid and eid not in owners:
                owners[eid]=self._read(eid,payload)['creator']
        if owners or 'entry_owners' in self.meta:
            self.meta['entry_owners']=pack(owners)
            self.db.execute("INSERT INTO metadata VALUES ('entry_owners',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",(self.meta['entry_owners'],))
        for gid, group in admin['groups'].items():
            self.db.execute('UPDATE groups SET payload=? WHERE id=?', (self._encode(group), gid))
        graph = {uid: {k: data['identity'][k] for k in ('id', 'box', 'sign', 'disabled')}
                 for uid, data in admin['users'].items()}
        for uid, data in admin['users'].items():
            graph[uid]['view_only'] = bool(data['identity'].get('view_only', False))
        groups = {gid: group['members'] for gid, group in admin['groups'].items()}
        excluded = {}
        for rule in admin['exclusions']:
            excluded.setdefault(rule['entry'], []).append(rule['user'])
        for uid, data in admin['users'].items():
            labels = {gid: group['name'] for gid, group in admin['groups'].items()
                      if uid in group['members'] or uid == self.meta['manager'].decode()}
            cap = {'vault': self.meta['vault_id'].decode(), 'user': uid, 'graph': graph,
                   'groups': groups, 'labels': labels, 'excluded': excluded,
                   'owners': json.loads(self.meta.get('entry_owners', b'{}'))}
            directory = SealedBox(PublicKey(un64(graph[uid]['box']))).encrypt(pack(sign(self._signer(), cap)))
            self.db.execute('UPDATE users SET directory=? WHERE id=?', (directory, uid))
        policy = {'vault': self.meta['vault_id'].decode(), 'hash': self._authority_hash()}
        # Keep this compatibility barrier once enabled: old engines reject the
        # extra signed field rather than silently granting write access.
        previous = json.loads(self.meta['authority'])['data'] if 'authority' in self.meta else {}
        features = set(previous.get('features', [])) | {'entry-ownership-v1'}
        if any(u.get('view_only') for u in graph.values()):features.add('view-only-users-v1')
        policy['features'] = sorted(features)
        authority = pack(sign(self._signer(), policy))
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
        members.add(self.owner_id(record))
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
        if self.ownership_enabled and eid not in self.cap.get('owners', {}):
            if eid.partition(':')[0] != record['creator'] or ':' not in eid:
                raise VaultError('Entry creator identity was changed or is not bound by the Manager.')
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
        record['owner'] = self.owner_id(record)
        return record

    def _can_write(self, record, uid):
        if uid == self.meta['manager'].decode():
            return True
        if uid in self.cap['excluded'].get(record['id'], []) or self.cap['graph'][uid]['disabled']:
            return False
        if self.ownership_enabled and uid == self.owner_id(record):
            return True
        if self.cap['graph'][uid].get('view_only', False):
            return False
        return uid == self.owner_id(record) or any(uid in self.cap['groups'].get(gid, []) for gid in record['groups'])

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
        record=dict(record);record.pop('owner',None)
        key = utils.random(32)
        envelope = {'vault': self.meta['vault_id'].decode(), 'id': record['id'], 'author': self.uid,
            'ciphertext': b64(secret.SecretBox(key).encrypt(pack(record))),
            'keys': {uid: b64(SealedBox(PublicKey(un64(self.cap['graph'][uid]['box']))).encrypt(key))
                     for uid in sorted(self._recipients(record))}}
        envelope['signed'] = sign(self._signer(), dict(envelope))
        self.db.execute('INSERT INTO entries VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                        (record['id'], pack(envelope)))

    @property
    def ownership_enabled(self):
        return bool(self.meta and 'entry-ownership-v1' in json.loads(self.meta['authority'])['data'].get('features', []))

    def owner_id(self, record):
        # The signed Manager policy is authoritative, never the mutable entry's
        # claimed owner. A former creator cannot sign themselves back in.
        return self.cap.get('owners', {}).get(record['id'], record['creator'])

    def owner_name(self, record):
        uid = self.owner_id(record)
        return 'You' if uid == self.uid else self.cap['graph'].get(uid, {}).get('name', 'Another user')

    @property
    def can_create(self):
        if not self.unlocked:return False
        self._refresh_cap()
        return self.ownership_enabled or self.can_edit

    def can_edit_entry(self, record):
        if not self.unlocked or not record:return False
        try:current=self._record(record['id'])
        except VaultError:return False
        return self._can_write(current,self.uid) and (not current.get('deleted') or self.manager)

    def enable_ownership(self):
        self._management_change(lambda: None)

    def set_owner(self, eid, uid):
        admin=self.administration()
        if uid not in admin['users'] or admin['users'][uid]['identity']['disabled']:
            raise VaultError('Choose an enabled user as the owner.')
        record=self._record(eid)
        if record.get('deleted'):raise VaultError('Restore the entry before changing its owner.')
        owners=json.loads(self.meta.get('entry_owners', b'{}'));owners[eid]=uid
        def operation():
            # Ownership implies access; remove any older exclusion for this user.
            for key,payload in list(self.db.execute('SELECT id,payload FROM exclusions')):
                if self._decode(payload)=={'entry':eid,'user':uid}:
                    self.db.execute('DELETE FROM exclusions WHERE id=?',(key,))
            self.db.execute("INSERT INTO metadata VALUES ('entry_owners',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",(pack(owners),))
        self._management_change(operation)

    @property
    def can_edit(self):
        if not self.unlocked:
            return False
        self._refresh_cap()
        return self.manager or not self.cap['graph'][self.uid].get('view_only', False)

    def set_view_only(self, uid, view_only):
        admin = self.administration()
        if uid == self.meta['manager'].decode() or uid not in admin['users']:
            raise VaultError('Choose an ordinary user; the Manager always has editing access.')
        data = admin['users'][uid]
        data['identity']['view_only'] = bool(view_only)
        self._management_change(lambda: self.db.execute(
            'UPDATE users SET recovery=? WHERE id=?', (self._encode(data), uid)))

    def save(self, record):
        if not self.unlocked:
            raise VaultError('Unlock first.')
        self._refresh_cap()
        if not self.can_create and not record.get('id'):
            raise VaultError('The Manager must enable owned-entry editing before you can create personal entries.')
        incoming = dict(record)
        existing = self._record(incoming['id']) if incoming.get('id') else None
        if 'owner' in incoming and incoming['owner'] != (self.owner_id(existing) if existing else self.uid):
            raise VaultError('Only the Manager can transfer ownership using Change Entry Owner.')
        if existing and (not self._can_write(existing, self.uid) or (existing.get('deleted') and not self.manager)):
            raise VaultError('You cannot edit this entry.')
        result = dict(existing or {'id': self.uid+':'+identifier() if self.ownership_enabled else identifier(), 'creator': self.uid, 'deleted': False})
        result.pop('owner', None)
        for field in ('description', 'link', 'user_name', 'password', 'notes'):
            result[field] = str(incoming.get(field, ''))
        if not result['description'].strip():
            raise VaultError('A description is required.')
        if self.manager or not existing:
            result['groups'] = list(dict.fromkeys(incoming.get('groups', [] if not self.can_edit else ([gid for gid,name in self.available_groups().items() if name == 'Generic'] if self.manager else list(self.available_groups())))))
            if (not result['groups'] and not self.ownership_enabled) or any(gid not in self.available_groups() for gid in result['groups']):
                raise VaultError('Choose valid groups, or enable owner permissions for a private entry.')
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

    def add_user(self, name, password, groups=None, *, view_only=False):
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
            if view_only:
                data=self.administration()['users'][uid]
                data['identity']['view_only']=True
                self.db.execute('UPDATE users SET recovery=? WHERE id=?',(self._encode(data),uid))
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

    def export_database(self,destination,*,overwrite=False):
        """Manager-only encrypted provision/recovery copy, without device settings."""
        self._admin_box()
        destination=Path(destination)
        if destination.is_symlink() or destination.resolve()==self.path.resolve() or (destination.exists() and os.path.samefile(destination,self.path)):
            raise VaultError('Choose an export file separate from the open vault.')
        from sync import read_settings
        folder=read_settings(self).get('folder')
        if folder and destination.resolve()==(Path(folder)/'wormwright-vault.sqlite').resolve():
            raise VaultError('Use Sync for the shared master; choose a separate export file.')
        if not overwrite or not destination.exists():
            self.backup(destination);return
        original=destination.stat()
        with tempfile.TemporaryDirectory(prefix='.wormwright-export-',dir=destination.parent) as temporary:
            staged=Path(temporary)/'export.sqlite';self.backup(staged)
            current=destination.stat()
            if (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)!=(original.st_dev,original.st_ino,original.st_size,original.st_mtime_ns):
                raise VaultError('The destination changed during export. Review it and try again.')
            os.replace(staged,destination)

    def reset_password(self, uid, password):
        admin = self.administration()
        if uid not in admin['users'] or not password:
            raise VaultError('Choose an account and a non-empty password.')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        wrapped = bytes(secret.SecretBox(derive(password, salt)).encrypt(pack(admin['users'][uid]['material'])))
        with self.db:
            self.db.execute('UPDATE users SET salt=?,credential=? WHERE id=?', (salt,wrapped,uid))

    def change_password(self, current_password, new_password, *, yubikey_settings=None, yubikey_response=None):
        if current_password is not None:self.verify_password(current_password)
        elif yubikey_settings is not None and yubikey_response is not None:self.verify_yubikey(yubikey_settings,yubikey_response)
        else:raise VaultError('Authenticate again before changing your password.')
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
            with destination.open('rb+') as stream:
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
            with staged.open('rb+') as stream:os.fsync(stream.fileno())
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

    def _hardware_row(self, db, username=''):
        meta = dict(db.execute('SELECT name,value FROM metadata'))
        if self.uid:
            return db.execute('SELECT id,hardware FROM users WHERE id=?', (self.uid,)).fetchone()
        if meta['mode'] == b'personal':
            return db.execute('SELECT id,hardware FROM users WHERE id=?', (meta['manager'].decode(),)).fetchone()
        login = hashlib.sha256(meta['vault_id'] + b'\0' + username.strip().casefold().encode()).hexdigest()
        return db.execute('SELECT id,hardware FROM users WHERE login=?', (login,)).fetchone()

    def yubikey_enrollments(self, username=''):
        from hardware_keys import decode
        if not self.path.is_file(): return []
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            row = self._hardware_row(db, username)
        if not row: return []
        return [dict(item, user=row[0]) for item in decode(row[1])]

    def yubikey_settings(self, username='', key_id=None):
        from hardware_keys import select
        return select(self.yubikey_enrollments(username), key_id)

    def enroll_yubikey(self, credential, salt, response, label=None):
        from vault import Vault
        from hardware_keys import decode, encode, append
        if not self.unlocked or len(salt) != 32:
            raise VaultError('Unlock the account and use a valid YubiKey salt.')
        self._refresh_cap()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT hardware FROM users WHERE id=?', (self.uid,)).fetchone()
            rows = decode(row[0])
            rows = append(rows, credential, salt, bytes(secret.SecretBox(Vault._hardware_key(response)).encrypt(pack(self.material))), label)
            self.db.execute('UPDATE users SET hardware=? WHERE id=?', (encode(rows), self.uid))

    def remove_yubikey(self, key_id):
        from hardware_keys import decode, encode
        if not self.unlocked: raise VaultError('Unlock the account first.')
        self._refresh_cap()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows = decode(self.db.execute('SELECT hardware FROM users WHERE id=?', (self.uid,)).fetchone()[0])
            remaining = [r for r in rows if r['id'] != key_id]
            if len(remaining) == len(rows): raise VaultError('Key enrollment changed. Try again.')
            self.db.execute('UPDATE users SET hardware=? WHERE id=?', (encode(remaining) if remaining else None, self.uid))

    def rename_yubikey(self, key_id, label):
        from hardware_keys import decode, encode, label_for
        if not self.unlocked: raise VaultError('Unlock the account first.')
        self._refresh_cap()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows = decode(self.db.execute('SELECT hardware FROM users WHERE id=?', (self.uid,)).fetchone()[0])
            selected = next((r for r in rows if r['id'] == key_id), None)
            if selected is None: raise VaultError('Key enrollment changed. Try again.')
            selected['label'] = label_for([r for r in rows if r['id'] != key_id], label)
            self.db.execute('UPDATE users SET hardware=? WHERE id=?', (encode(rows), self.uid))

    def unlock_yubikey(self, settings, response):
        from vault import Vault
        self.lock()
        try:
            self._connect()
            self.uid = settings['user']
            if self.yubikey_settings(key_id=settings.get('id')) != settings:
                raise VaultError('YubiKey enrollment changed. Try again.')
            self.material = json.loads(secret.SecretBox(Vault._hardware_key(response)).decrypt(settings['wrapped_key']))
            self._refresh_cap()
            self.entries(include_deleted=self.manager)
        except Exception as error:
            self.lock()
            raise VaultError('Cannot unlock this account with the YubiKey.') from error

    def verify_yubikey(self, settings, response):
        from vault import Vault
        if not self.unlocked or settings != self.yubikey_settings(key_id=settings.get('id')):
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


