"""Three-way decisions over encrypted entry fingerprints, never plaintext history."""
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path


def state(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        metadata = hashlib.sha256()
        for name, value in db.execute('SELECT name,value FROM metadata ORDER BY name'):
            for part in (name.encode(), value):
                metadata.update(len(part).to_bytes(8, 'big'))
                metadata.update(part)
        return {'version': 1, 'metadata': metadata.hexdigest(),
                'entries': {key: hashlib.sha256(payload).hexdigest()
                            for key, payload in db.execute('SELECT id,payload FROM entries')}}


def decisions(base, local, shared):
    """Absent entries distinguish deletes from additions against the saved baseline."""
    if not base or base.get('version') != 1:
        return None
    # Authentication changes need explicit review rather than combining envelopes.
    if local['metadata'] != shared['metadata']:
        return None
    result = {}
    for key in base['entries'].keys() | local['entries'].keys() | shared['entries'].keys():
        old = base['entries'].get(key)
        ours = local['entries'].get(key)
        theirs = shared['entries'].get(key)
        result[key] = ('local' if ours == theirs else 'shared' if ours == old
                       else 'local' if theirs == old else None)
    return result
