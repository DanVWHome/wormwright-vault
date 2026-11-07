"""Bounded, named hardware-key envelopes. Reads legacy single-key documents.
No PINs or hardware response secrets are stored here.
"""
import base64
import hashlib
import json
import uuid
from vault import VaultError

MAX_KEYS = 4
FIELDS = ('credential', 'salt', 'wrapped_key')


def decode(raw, *, legacy_version=False):
    if raw is None:
        return []
    try:
        document = json.loads(raw)
        if document.get('version') == 2:
            rows = document['keys']
        else:
            if legacy_version and document.get('version') != 1:
                raise ValueError()
            rows = [document]
        if not isinstance(rows, list) or len(rows) > MAX_KEYS:
            raise ValueError()
        result = []
        for row in rows:
            item = dict(row)
            for field in FIELDS:
                item[field] = base64.b64decode(item[field], validate=True)
            if not item['credential'] or len(item['salt']) != 32 or not item['wrapped_key']:
                raise ValueError()
            item.setdefault('id', hashlib.sha256(item['credential']).hexdigest())
            item.setdefault('label', 'Original key')
            if not isinstance(item['id'], str) or not item['id'] or not isinstance(item['label'], str):
                raise ValueError()
            result.append(item)
        if len({r['id'] for r in result}) != len(result) or len({r['credential'] for r in result}) != len(result):
            raise ValueError()
        return result
    except Exception as e:
        raise VaultError('Invalid or unsupported YubiKey configuration. Existing data was kept.') from e


def encode(rows):
    data = []
    for row in rows:
        item = dict(row)
        item.pop('user', None)
        for field in FIELDS:
            item[field] = base64.b64encode(item[field]).decode()
        data.append(item)
    return json.dumps({'version': 2, 'keys': data}, sort_keys=True).encode()


def label_for(rows, label):
    if len(rows) >= MAX_KEYS:
        raise VaultError('Four keys are already enrolled. Remove one before adding another.')
    label = label.strip() if label else next('Key '+str(i) for i in range(1, MAX_KEYS+2) if 'key '+str(i) not in {r['label'].casefold() for r in rows})
    if not label or len(label) > 64 or any(ord(c) < 32 for c in label):
        raise VaultError('Use a key name of 1–64 characters.')
    if label.casefold() in {r['label'].casefold() for r in rows}:
        raise VaultError('That key name is already used. Choose another name.')
    return label


def append(rows, credential, salt, wrapped_key, label=None, *, legacy_version=False):
    label = label_for(rows, label)
    if any(r['credential'] == credential for r in rows):
        raise VaultError('This credential is already enrolled.')
    item = dict(id=uuid.uuid4().hex, label=label, credential=credential, salt=salt, wrapped_key=wrapped_key)
    if legacy_version:
        item['version'] = 1
    return [*rows, item]


def select(rows, key_id=None):
    if key_id is None:
        return rows[0] if rows else None
    return next((r for r in rows if r['id'] == key_id), None)
