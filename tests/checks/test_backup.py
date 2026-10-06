from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(SOURCE))
from vault import Vault, VaultError
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    v=Vault(root/'vault.sqlite')
    pw='test-master-passphrase'
    v.create(pw)
    record=dict(description='Backup test', link='', user_name='demo', password='encrypted-secret', notes='')
    entry_id=v.save(record)
    backup=root/'backup.sqlite'
    v.backup(backup)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert b'encrypted-secret' not in backup.read_bytes()
    try:
        v.backup(backup)
        raise AssertionError('overwrote existing file')
    except FileExistsError:
        pass
    v.save({**record, 'id':entry_id, 'description':'Later edit'})
    for source,password in [(backup,'wrong'),(root/'missing.sqlite',pw),(v.path,pw)]:
        try:
            v.restore(source,password)
            raise AssertionError('accepted invalid restore')
        except Exception as error:
            assert not isinstance(error, AssertionError)
        assert v.entries()[0]['description']=='Later edit'
    bad=root/'bad.sqlite'
    bad.write_bytes(b'not a database')
    try:
        v.restore(bad,pw)
        raise AssertionError('accepted damaged file')
    except Exception as error:
        assert not isinstance(error, AssertionError)
    safety=v.restore(backup,pw)
    assert v.unlocked
    v.unlock(pw)
    assert v.entries()[0]['description']=='Backup test'
    previous=Vault(safety)
    previous.unlock(pw)
    assert previous.entries()[0]['description']=='Later edit'
    previous.lock()
    assert not list(root.glob('.atlas-restore-*'))
    v.lock()
print('PASS: encrypted snapshot, overwrite protection, invalid restore preserves current vault, restore, safety backup, staging cleanup')
