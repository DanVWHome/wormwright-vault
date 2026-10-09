# Wormwright Vault 0.3.2 — Linux Mint release

Supports Linux Mint 22.x, Intel/AMD 64-bit (amd64), glibc 2.39 or newer.
Cinnamon and XFCE are the intended desktop environments. Earlier Mint versions,
ARM systems and other distributions are not included in this support claim.
The installer includes Vault and optional Vault Manager, searchable offline Help,
an optional synthetic demo, About and the narrated tutorial recorded on 0.2.13.

## Install or upgrade

Download `wormwright-vault-mint_0.3.2_amd64.deb` from the public GitHub release.
Before upgrading, make an encrypted backup of each working vault and close both
apps. Install with:

```bash
sudo apt install ~/Downloads/wormwright-vault-mint_0.3.2_amd64.deb
```

APT replaces the managed beta package. It keeps the current-format vault files,
credentials, per-device locations, sync settings and backups where they are.
The existing `wormwright-vault-beta` and Manager shortcut commands remain aliases.
The application menu now shows Wormwright Vault and Wormwright Vault Manager.
The older personal prototype package is separate. No database conversion occurs.
The historical `wormwright-vault-beta` device-settings folder is retained so the
upgrade remembers existing vault locations. It is not a requirement to store
working vaults there.

Confirm 0.3.2 in the heading. Confirm the chosen local vault and Sync Settings,
then verify one synthetic sync entry before continuing daily use. Keep the local
working database off the NAS; use a dedicated mounted folder for the shared
master. SMB and FTP mounts must support the required filesystem operations.
VPN/Twingate provides network access, not a separate sync protocol.

## Scope and security limits

This is the first Linux Mint release after automated checks and reported testing
across three computers, including offline edits, conflicts, FTP and SMB sync.
It has not undergone an independent security audit. Hardware and NAS behavior
still need checking on each installation. Per-user encryption, signed policies,
YubiKey PIN/touch with password fallback, inactivity locking, clipboard clearing,
deleted-entry recovery and Manager administration are included.

An old disconnected copy or backup can retain passwords and previous access.
Revocation takes effect after a successful sync and cannot erase prior knowledge.
Keep encrypted backups; an unavailable share leaves changes saved only locally.
CSV exports contain readable passwords and must be handled accordingly.
Do not send real vaults, CSV exports, passwords, keys or NAS credentials in bug
reports. Use synthetic entries and describe the version and behavior.

The AI hook accepts UI-only commands and returns no secrets. For an explicit
working vault path, use `wormwright-control-mint lookup Gmail --vault /path/to/local.sqlite`.
It selects masked search results or presents authentication. Run in the normal
desktop session for physical YubiKey access.

Android is next, targeting Pixel 10 with GrapheneOS. No Android installer or
compatibility claim is part of this release.

## Delete a local vault or its backups

Vault → Delete Local Vault removes the working file and disconnects its local sync settings. Import / Export / Backup → Delete Vault Backups lists matching local/NAS backup copies and lets you add other backup files. Select individual backups or all listed backups. Both actions require an unlocked Manager account, fresh password or YubiKey authentication, exact-file review and typing DELETE. NAS master copies and other devices remain. Deletion does not guarantee forensic erasure or removal of external snapshots.

Vault → Delete Shared NAS Vault is a separate Manager-authorized action for the configured shared master. Disconnect sync on every other device first: another client can recreate the NAS master from its local copy. The command requires current NAS Manager access, refuses a busy NAS sync lock, reviews the exact path, and disconnects this computer. Local copies and backups remain.
