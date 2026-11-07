"""A private, bounded local socket must work even for very long vault paths."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from hooks import endpoint, LocalControl, send

with tempfile.TemporaryDirectory(prefix='wormwright-path-') as directory:
    root=Path(directory)
    long_folder=root / ('long-vault-location-'*8)
    long_folder.mkdir()
    vault=long_folder/'invented.sqlite'
    for runtime in (str(root), str(long_folder), str(root/'missing'), '/tmp'):
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR':runtime}):
            path=endpoint(vault)
            assert len(os.fsencode(path))<104
            assert not path.is_relative_to(vault.parent)
            assert path.parent.stat().st_uid==os.getuid()
            assert path.parent.stat().st_mode & 0o077==0
            assert endpoint(vault)==path and endpoint(vault.with_name('other.sqlite'))!=path
            service=LocalControl(vault,lambda request:None)
            result=[]
            thread=threading.Thread(target=lambda:result.append(send(vault,{'version':1,'action':'capabilities'})))
            thread.start()
            deadline=time.monotonic()+4
            while thread.is_alive() and time.monotonic()<deadline:
                service.poll(); time.sleep(.005)
            thread.join(timeout=1)
            service.close()
            assert not thread.is_alive() and result[0]['returns_secrets'] is False
            assert not vault.exists()
    private=root/'private-runtime';private.mkdir(mode=0o700)
    other=root/'other';other.mkdir()
    (private/'wormwright-control').symlink_to(other,target_is_directory=True)
    with patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(private)}):
        try:endpoint(vault);raise AssertionError('Accepted symlink control directory')
        except ValueError:pass
print('PASS: short local socket, long and missing runtime fallback, private ownership, symlink rejection, actual local requests')
