"""GVFS upload fault injection; never touch real vaults or mounts."""
import builtins,errno,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from managed_sync import _replace
from vault import VaultError
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);source=root/'source.sqlite';share=root/'share';share.mkdir();target=share/'master.sqlite'
 source.write_bytes(b'synthetic encrypted snapshot');target.write_bytes(b'previous snapshot')
 real_open=builtins.open
 def gvfs_open(path,mode='r',*args,**kwargs):
  if '+' in mode and Path(path).parent==share:raise OSError(errno.ENOTSUP,'GVFS rejects O_RDWR')
  return real_open(path,mode,*args,**kwargs)
 with patch('builtins.open',side_effect=gvfs_open):_replace(source,target)
 assert target.read_bytes()==source.read_bytes()
 with patch('managed_sync.os.fsync',side_effect=OSError(errno.ENOTSUP,'no fsync')):_replace(source,target)
 assert target.read_bytes()==source.read_bytes()
 target.write_bytes(b'previous snapshot')
 with patch('managed_sync.os.fsync',side_effect=OSError(errno.EIO,'NAS I/O failure')):
  try:_replace(source,target)
  except OSError as error:assert error.errno==errno.EIO
  else:raise AssertionError('I/O failures must stop publication')
 assert target.read_bytes()==b'previous snapshot'
 import managed_sync
 original=managed_sync.shutil.copyfileobj
 def corrupt(origin,destination):destination.write(b'truncated snapshot')
 with patch('managed_sync.shutil.copyfileobj',side_effect=corrupt):
  try:_replace(source,target)
  except VaultError as error:assert 'verification failed' in str(error)
  else:raise AssertionError('Corrupted upload must not replace the master')
 assert target.read_bytes()==b'previous snapshot'
 assert not list(share.glob('.wormwright-managed-*'))
print('GVFS modes, unsupported fsync, I/O errors and corrupted-upload protection passed.')
