from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys, tempfile, sqlite3
from pathlib import Path
sys.path.insert(0, str(SOURCE))
from vault import Vault, VaultError
from nacl.exceptions import CryptoError
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'vault.sqlite'
    vault = Vault(path)
    vault.create('test-master-passphrase')
    record = dict(description='Private description', link='https://private.example', user_name='private-user', password='unique-secret-123', notes='private notes')
    entry_id = vault.save(record)
    vault.save({**record, 'id': entry_id, 'notes': 'updated secret notes'})
    assert len(vault.entries()) == 1
    assert vault.entries()[0]['notes'] == 'updated secret notes'
    vault.lock()
    if sys.platform != "win32":
        assert path.stat().st_mode & 0o777 == 0o600
    raw = path.read_bytes()
    assert all(value.encode() not in raw for value in record.values())
    try:
        vault.unlock('wrong-passphrase')
        raise AssertionError('Wrong password accepted')
    except VaultError:
        assert not vault.unlocked
    vault.unlock('test-master-passphrase')
    assert vault.entries()[0]['password'] == record['password']
    vault.delete(entry_id)
    assert vault.entries() == []
    vault.save(record)
    vault.lock()
    db = sqlite3.connect(path)
    payload = db.execute('SELECT payload FROM entries').fetchone()[0]
    tampered = payload[:-1] + bytes([payload[-1] ^ 1])
    db.execute('UPDATE entries SET payload=?', (tampered,))
    db.commit()
    db.close()
    try:
        vault.unlock('test-master-passphrase')
        raise AssertionError('Tampered record accepted')
    except VaultError:
        assert not vault.unlocked
print('PASS: create, encrypted fields, permissions, update, lock, wrong password, reopen, delete, tamper rejection')
