"""Encrypted share transfers avoid chmod and distinguish unsupported fsync from I/O failure."""
import errno,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_sync import _retained,_replace
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);source=root/'source';source.write_bytes(b'encrypted-test-snapshot')
    target=root/'wormwright-vault.sqlite';target.write_bytes(b'old-encrypted-copy')
    with patch.object(Path,'chmod',side_effect=OSError(errno.ENOTSUP,'Unsupported')):
        directory,prefix,limit=_retained(source,target,10)
    assert next(directory.glob(prefix+'*.sqlite')).read_bytes()==source.read_bytes()
    with patch('managed_sync.os.fsync',side_effect=OSError(errno.ENOTSUP,'Unsupported')):_replace(source,target)
    assert target.read_bytes()==source.read_bytes()
    target.write_bytes(b'keep-original')
    with patch('managed_sync.os.fsync',side_effect=OSError(errno.EIO,'Disk I/O error')):
        try:_replace(source,target)
        except OSError as error:assert error.errno==errno.EIO
        else:raise AssertionError('Suppressed real disk failure')
    assert target.read_bytes()==b'keep-original'
    assert not list(root.glob('.wormwright-managed-*.sqlite'))
print('Share permission/flush compatibility and original preservation checks passed')
