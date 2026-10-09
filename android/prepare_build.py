"""Prepare a synthetic sample and private, persistent preview signing identity."""
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'app/src/main/python'))
from managed_vault import ManagedVault

assets = ROOT / 'app/src/main/assets'
assets.mkdir(parents=True, exist_ok=True)
sample = assets / 'sample-vault.db'
if not sample.exists():
    vault = ManagedVault(sample)
    vault.create('SampleOnly-October2026!', username='Demo')
    for description, user, website, password in [
        ('Sample email', 'demo@example.invalid', 'https://mail.example.invalid', 'Invented-Email-Password!'),
        ('Sample home server', 'demo-admin', 'https://nas.example.invalid', 'Invented-NAS-Password!'),
        ('Sample café account', 'coffee-demo', 'https://cafe.example.invalid', 'Invented-Cafe-Password!'),
    ]:
        vault.save({'description': description, 'user_name': user, 'link': website,
                    'password': password, 'notes': 'Invented entry for Android testing. No real account.'})
    vault.lock()

signing = ROOT.parent / 'tools/signing'
signing.mkdir(parents=True, exist_ok=True, mode=0o700)
properties = signing / 'preview.properties'
password_file = signing / 'password.txt'
if not properties.exists():
    password = secrets.token_urlsafe(40)
    properties.write_text('password=' + password + '\n')
    properties.chmod(0o600)
    password_file.write_text(password + '\n')
    password_file.chmod(0o600)
key = signing / 'preview.jks'
if not key.exists():
    subprocess.run(['keytool', '-genkeypair', '-keystore', str(key), '-storetype', 'JKS',
        '-storepass:file', str(password_file), '-keypass:file', str(password_file),
        '-alias', 'wormwright-preview', '-keyalg', 'RSA', '-keysize', '3072',
        '-validity', '10000', '-dname', 'CN=Wormwright Vault Preview, O=Wormwright'], check=True)
    key.chmod(0o600)
print('Sample vault and private preview signing identity ready.')
