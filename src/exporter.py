"""Explicit plaintext CSV export, compatible with the vault importer."""
import csv
import os
from pathlib import Path
from vault import VaultError


def export_csv(vault, destination, *, password=None, yubikey_settings=None, yubikey_response=None):
    if not vault.unlocked:
        raise VaultError('Unlock the vault before exporting.')
    if password is not None:
        vault.verify_password(password)
    elif yubikey_settings is not None and yubikey_response is not None:
        vault.verify_yubikey(yubikey_settings, yubikey_response)
    else:
        raise VaultError('Authenticate again before exporting passwords.')
    destination = Path(destination)
    # Never overwrite a vault, existing export, or another file.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['description', 'link', 'user_name', 'pw', 'notes'])
            writer.writeheader()
            for record in vault.entries():
                writer.writerow({field: record.get('password' if field == 'pw' else field, '') for field in writer.fieldnames})
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
