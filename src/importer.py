"""Read Atlas CSV exports without executing PHP or writing decrypted files."""
import base64
import csv
from pathlib import Path


class ImportErrorDetail(ValueError):
    pass


def read_export(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        required = {'description', 'link', 'user_name', 'pw', 'notes'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ImportErrorDetail('CSV needs description, link, user_name, pw, and notes column headers.')
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or any(row.get(field) is None for field in required):
                raise ImportErrorDetail(f'Row {number} has an incorrect number of columns.')
            if not row['description'].strip():
                raise ImportErrorDetail(f'Row {number} needs a description.')
            rows.append({'description': row['description'], 'link': row['link'], 'user_name': row['user_name'], 'password': row['pw'], 'notes': row['notes']})
    if not rows:
        raise ImportErrorDetail('CSV contains no entries.')
    return rows


def decode_legacy(rows, key, iv):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    if len(iv.encode()) != 16:
        raise ImportErrorDetail('The legacy initialization vector must be exactly 16 bytes.')
    if not key:
        raise ImportErrorDetail('Enter the encryption key used when this export was created.')
    aes_key = key.encode().ljust(16, b'\0')[:16]  # PHP OpenSSL AES-128 passphrase behavior.
    result = []
    for number, row in enumerate(rows, 1):
        try:
            decryptor = Cipher(algorithms.AES(aes_key), modes.CTR(iv.encode())).decryptor()
            encrypted = base64.b64decode(row['password'], validate=True)
            password = (decryptor.update(encrypted) + decryptor.finalize()).decode('utf-8')
            if any(ord(character) < 32 or ord(character) == 127 for character in password):
                raise ValueError('Unexpected control character')
        except (ValueError, UnicodeError) as error:
            raise ImportErrorDetail(f'Could not decode password in entry {number}. Check the source format, key, and initialization vector. Nothing has been imported.') from error
        result.append({**row, 'password': password})
    return result
