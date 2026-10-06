"""Verify plaintext round trips and export failure boundaries with dummy data."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from vault import Vault, VaultError
from importer import read_export
from exporter import export_csv

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    vault = Vault(root / 'dummy.sqlite')
    vault.create('disposable-master-password')
    record = dict(description='Demo, ünicode', link='https://example.com', user_name='demo', password='dummy,"password', notes='two\nlines')
    vault.save(record)
    destination = root / 'export.csv'
    export_csv(vault, destination, password='disposable-master-password')
    assert read_export(destination) == [record]
    assert destination.stat().st_mode & 0o777 == 0o600
    before = destination.read_bytes()
    try:
        export_csv(vault, destination, password='disposable-master-password')
        raise AssertionError('Existing file overwritten')
    except FileExistsError:
        pass
    assert destination.read_bytes() == before
    failed = root / 'failed.csv'
    with patch.object(vault, 'entries', side_effect=VaultError('Dummy validation failure')):
        try:
            export_csv(vault, failed, password='disposable-master-password')
            raise AssertionError('Failure ignored')
        except VaultError:
            pass
    assert not failed.exists()
    for authorization in ({}, {'password': 'wrong-password'}):
        rejected = root / 'rejected.csv'
        try:
            export_csv(vault, rejected, **authorization)
            raise AssertionError('Missing or incorrect authentication accepted')
        except VaultError:
            pass
        assert not rejected.exists()
    response = b'x' * 32
    vault.enroll_yubikey(b'dummy-credential', b's' * 32, response)
    settings = vault.yubikey_settings()
    export_csv(vault, root / 'key.csv', yubikey_settings=settings, yubikey_response=response)
    try:
        export_csv(vault, root / 'wrong-key.csv', yubikey_settings=settings, yubikey_response=b'z' * 32)
        raise AssertionError('Wrong key accepted')
    except VaultError:
        pass
    assert not (root / 'wrong-key.csv').exists()
    vault.lock()
    try:
        export_csv(vault, root / 'locked.csv')
        raise AssertionError('Locked export allowed')
    except VaultError:
        pass
    assert not (root / 'locked.csv').exists()
print('PASS: CSV round trip, permissions, no overwrite, failure cleanup and locked export rejection')
