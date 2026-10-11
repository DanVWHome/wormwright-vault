"""Open a GVFS NAS master as a paired, device-local managed working copy."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from managed_vault import ManagedVault
from managed_sync import state
from platform_paths import data_home
from sync import configure, read_settings, settings_path, atomic_json
from vault import VaultError


def is_nas_path(path):
    parts = Path(path).parts
    return any(part.startswith('smb-share:') and index > 0 and parts[index - 1] in ('gvfs', '.gvfs')
               for index, part in enumerate(parts))


def prepare_managed_vault(path):
    path = Path(path).resolve()
    if not is_nas_path(path):
        return path
    if path.name != 'wormwright-vault.sqlite':
        raise VaultError('Choose the shared master named wormwright-vault.sqlite in your NAS sync folder.')
    identity = hashlib.sha256(os.fsencode(path)).hexdigest()[:32]
    directory = data_home() / 'wormwright-vault-beta/nas-copies' / identity
    if is_nas_path(directory):
        raise VaultError('Choose a local application data folder before opening a NAS vault.')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    local = directory / 'vault.sqlite'
    # Serialize first-time setup without taking or changing a NAS sync lock.
    import fcntl
    descriptor = os.open(directory / '.setup.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        created = False
        baseline = None
        if not local.exists():
            if (path.parent / '.wormwright-sync-lock').exists():
                raise VaultError('Another device is syncing this vault. Try opening it again when sync finishes.')
            if any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-journal')):
                raise VaultError('The NAS vault has unfinished database writes. Close the app using that shared file before trying again.')
            fd, name = tempfile.mkstemp(prefix='.nas-copy-', suffix='.sqlite', dir=directory)
            try:
                with os.fdopen(fd, 'wb') as target, path.open('rb') as source:
                    shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
                baseline = state(name)  # Validate the encrypted format and authority signature.
                os.replace(name, local)
                created = True
            finally:
                Path(name).unlink(missing_ok=True)
        else:
            baseline = state(local)
        vault = ManagedVault(local)
        previous = read_settings(vault)
        folder = str(path.parent)
        if previous.get('folder') and Path(previous['folder']).resolve() != path.parent:
            raise VaultError('This local working copy is linked to another shared folder. Its sync settings were preserved.')
        if not previous.get('folder'):
            configure(vault, folder, previous.get('limit', 10), previous.get('automatic', True), previous.get('interval', 30))
            if created:
                config = read_settings(vault)
                config['managed_baseline'] = baseline
                atomic_json(settings_path(vault), config)
        # Reopening preserves local edits, baseline, and per-device preferences.
        return local
    finally:
        os.close(descriptor)
