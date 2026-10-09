"""Cross-platform format, merge, backup and NAS regressions using dummy data."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

checks = Path(__file__).resolve().parent / 'checks'
names = ['vault', 'managed_vault', 'sync', 'managed_sync', 'merge_sync',
         'sync_settings_baseline', 'sync_lock_cleanup', 'gvfs_upload', 'conflicts', 'history', 'backup', 'import',
         'export', 'fido_protocol', 'windows_control', 'windows_local_sync', 'windows_debug', 'update_check', 'vault_cleanup', 'vault_names']
if sys.platform != 'win32':
    names.append('requests')
with tempfile.TemporaryDirectory(prefix='wormwright-portable-') as directory:
    environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                   'XDG_DATA_HOME': directory, 'LOCALAPPDATA': directory,
                   'XDG_RUNTIME_DIR': directory}
    for name in names:
        check = checks / ('test_' + name + '.py')
        print(check.name, flush=True)
        subprocess.run([sys.executable, str(check)], cwd=directory, env=environment, check=True)
print('Portable dummy-data checks passed.')
