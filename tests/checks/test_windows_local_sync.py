"""Windows local snapshot application with an existing SQLite reader."""
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
import managed_sync
from managed_vault import ManagedVault
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    vault = ManagedVault(root / 'local.sqlite');vault.create('synthetic-manager-password')
    entry = vault.save({'description': 'Before', 'password': 'encrypted-secret'})
    source = root / 'snapshot.sqlite';vault.backup(source)
    other = ManagedVault(source);other.resume(vault.session())
    other.save({**other._record(entry), 'description': 'After'});other.lock()
    session = vault.session()
    with patch.object(managed_sync.sys, 'platform', 'win32'):
        managed_sync._replace_local(source, vault.path)
    vault.resume(session)
    assert vault._record(entry)['description'] == 'After'
    assert b'encrypted-secret' not in vault.path.read_bytes()
    vault.lock()
print('PASS: transactional local snapshot update with an open SQLite connection.')
