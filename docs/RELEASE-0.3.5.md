# Wormwright Vault 0.3.5

Vault and Manager on Linux and Windows now include Vault → Delete Local Vault and Import / Export / Backup → Delete Vault Backups.

Both require an unlocked Manager account, fresh password or enrolled YubiKey authorization, a review of exact files, and typing DELETE. Cancelling or failing authorization removes nothing. Local deletion disconnects local sync before removing the working database and its SQLite sidecars. NAS masters and other devices are preserved. Do not leave another process editing or syncing a selected file while deleting it.

Backup cleanup discovers matching vault copies in the working folder and configured NAS backup folders. Select individual copies or all listed copies, and add manual backup files from other locations. Unrelated vaults, symlinks, working/shared masters and changed files are rejected. Copies on unavailable devices, unselected files and provider trash remain. File removal does not guarantee forensic erasure from flash storage or deletion of external snapshots.

Create New Vault remains available after deletion. Keep a backup unless you deliberately intend to destroy all recovery paths. Shared vaults must be deleted separately on each device; stop using their sync connections first.

Vault → Delete Shared NAS Vault is a separate Manager-authorized action for the configured shared master. Disconnect sync on every other device first: another client can recreate the NAS master from its local copy. The command requires current NAS Manager access, refuses a busy NAS sync lock, reviews the exact path, and disconnects this computer. Local copies and backups remain.
