"""Release our NAS lock without altering locks held by other syncs."""
import time
from vault import VaultError


def release_lock(lock):
    for attempt in range(3):
        try:
            lock.rmdir()
            return
        except OSError as error:
            if attempt == 2:
                raise VaultError(
                    'Sync finished or stopped, but its NAS lock could not be removed. '
                    'The NAS connection or permissions may have changed. '
                    'Check that every device has stopped syncing before clearing '
                    '.wormwright-sync-lock. Details: ' + str(error)
                ) from error
            time.sleep(0.2 * (attempt + 1))
