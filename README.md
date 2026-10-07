# Wormwright Vault

An offline Linux password-vault prototype by Dan Van Wormer with AI assistance.
Built for Linux Mint Cinnamon and XFCE. Entry passwords and metadata are
locally encrypted; optional YubiKey PIN plus touch and a separate password
fallback unlock the vault.

## Install the prototype

The supplied `wormwright-vault_0.1.14_amd64.deb` targets **Linux Mint 22.x on
Intel/AMD 64-bit computers** (glibc 2.39 or newer). It bundles Python, Qt,
and encryption libraries. It does not download Python packages at launch.
APT may download the Linux display and FIDO-permission prerequisites during
installation. Mint 21 needs a build made on its older base; this particular
binary is not claimed compatible with it.

```sh
sudo apt install ./wormwright-vault_0.1.14_amd64.deb
```

Open **Wormwright Vault** from the application menu. If the key is not detected
immediately after installation, unplug and reconnect it to apply the installed
FIDO device permissions. Run the app as your normal user.

Existing prototype vaults under `~/.local/share/atlas-portable` are reused.
New vaults default to `~/.local/share/vanwormai-vault`. Installing or removing
the package does not import, replace, or delete a user's vault.

## Assistant lookup

```sh
wormwright-control lookup Gmail
wormwright-control open
wormwright-control lock
```

These commands select masked entries or show the unlock screen. They return
only acknowledgments, not passwords, records, or match counts.

An assistant-launched subprocess can inherit the assistant's USB restrictions.
For voice requests to start the GUI in your ordinary desktop session, enable
this **optional** fixed-action launcher from your own terminal after installing:

```sh
wormwright-enable-desktop-launcher
```

It starts a small local launcher now and on future logins. It runs as your user,
accepts only the versioned UI-request allowlist, and cannot unlock or reveal
passwords. It has no network listener or administrator privileges. Close any
previous sandbox-launched instance before trying the desktop launcher. Normal
menu launches do not require this option. Actual host-session USB behavior
must be tested on each machine; packaging alone does not remove an outer sandbox.

To disable future autostart, remove
`~/.config/autostart/vanwormai-vault-agent.desktop` and log out and back in.
Full UI/backup/import instructions are in [docs/README.txt](docs/README.txt),
and the hook contract is in [docs/INTEGRATION.txt](docs/INTEGRATION.txt).

## Develop from source

Python 3.10+ is required. On Mint, install `python3-venv`, `libxcb-cursor0`,
and `libxkbcommon-x11-0` if needed, then run:

```sh
chmod +x start.sh control.sh
./start.sh
```

The first source launch downloads dependencies into `.venv`.
Initial master passwords require twelve characters; subsequent fallback
passwords can be any non-empty length. Reusing your Linux password is a
choice of value, not authentication against sudo/PAM.

## Tests and packaging

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python tests/run_checks.py
.venv/bin/python packaging/build-deb.py
```

The test suite uses temporary dummy vaults and synthetic FIDO assertions.
It covers encryption/tamper handling, edits, backups/restores, migration
validation, PIN/touch verification flags, password fallback, masked lookup,
private local IPC and single-instance handling. It never loads real vaults.

The build script stages an explicit source allowlist and produces a bundled
`.deb` under `dist/`. Build on the oldest supported target distribution, and
set `--glibc-min` to the minimum supported libc version for that build.
The build tool is pinned; this is not yet a bit-for-bit reproducible release.

## Repository boundary

Only application source, dummy-data tests, documentation, and packaging files
belong in Git. Vault databases, CSV exports, backups, keys, environments, build
outputs and crash dumps are excluded. Installer artifacts are delivered
separately. No uploaded Atlas files or personal export is part of this repository.

This remains a prototype. Forgotten-password recovery is not implemented. Shared-folder sync is manual
and stops on conflicting edits; it does not merge records. Physical YubiKey enrollment/unlock and installer behavior
must be checked on each target laptop/desktop before using real credentials.
No application license has been selected; keep the repository private for now.
Third-party component licenses remain applicable to bundled dependencies.

## Wormwright AI branding

The approved family reference is `assets/wormwright-mascot-reference.png`.
Use the same coral cartoon worm, broad curled pose, head tilt, navy outlines,
and cream AI badge with sparkle for future app variants. Maintain a complete,
readable body silhouette. Main and Email poses are approved; place Vault and
Notes props beside the worm. Avoid circuit traces, hook-shaped poses and cut-off limbs.
The Vault icon is `assets/wormwright-vault.png`.

Version 0.1.2 changes the display branding and icon. The installed package keeps
its original `vanwormai-vault` identity to upgrade existing installations.
Old command names, data paths, local-control endpoint and FIDO relying-party
identity are retained for compatibility. The `wormwright-*` commands are the
preferred aliases. No vault or key reenrollment is required.

## Shared-folder sync

Keep a separate local working vault on each machine. Mount a dedicated home-server
folder using your normal network-share tools (over any VPN that allows access).
Unlock the vault, open **Sync Settings**, choose that mounted folder, then click
**Sync Now**. The shared copy is named `wormwright-vault.sqlite`. Never open that
shared copy directly for editing. Do not use a cloud-mirrored folder.

The first device uploads its vault. Copy that shared vault to a local file on the
next device, unlock the local copy, choose the same shared folder, and sync once
to pair it. Thereafter local-only changes upload and server-only changes download.
Downloads refresh the authenticated session without locking. Future unlocks use the credentials in the updated copy.
Fallback-password and YubiKey changes travel with the vault. Old backups retain
their old credentials. When both copies changed, sync stops without overwriting;
keep both files and reconcile the entries manually. There is no force-overwrite
button or automatic merge.

Automatic sync backups default to **10 per working/shared copy**. Change the limit
in Sync Settings (1–1000). Each successful transfer backs up the copy it replaces;
uploads also back up the local working copy. Successful syncs prune only older
files belonging to that copy inside `.wormwright-sync-backups`. Manual backups
and import/restore/authentication safety backups are not pruned. Syncs with no
changes create no new backups but apply the current limit.

Local pairing/settings live beside the local vault in `<vault>.sync.json`; keep
that file on its originating device. Do not copy it to pair another machine.
A missing shared copy after pairing is treated as a conflict, not recreated.
Mount the share before syncing. All devices must use Sync Now; other programs
editing the shared database do not participate in the sync lock. A crashed sync
may leave `.wormwright-sync-lock` in the share: verify no device is syncing
before removing that empty lock directory. Server backups remain advisable;
automatic retained versions are not forgotten-password recovery.

## CSV import and export

**Import Vault CSV** previews plain-text vault exports. No legacy
encryption format, encryption key, or initialization vector is requested. **Export to CSV** exports every
entry, including passwords and notes, regardless of the current search.
Export requires an explicit plain-text warning confirmation, creates a new
file with owner-only permissions, and never overwrites an existing file.
Columns are `description,link,user_name,pw,notes`, matching the importer.
CSV preserves field values exactly; use it for transfer rather than opening
untrusted entries in spreadsheet software, which can interpret formulas.
Use **Back Up Vault** when you want an encrypted backup.

Every CSV export requires fresh authentication: the enrolled YubiKey with PIN
and touch, or the current fallback/master password. Being unlocked alone is
not sufficient. Cancelled or failed authentication creates no export file.

Creating a new vault opens one dialog with New master password and Confirm
master password fields. Both must match and contain at least 12 characters.
Cancelling creates no vault; existing vault unlock uses its current password.

Each main-table Show button opens a separate, resizable window with 32-point
monospace password text. The table stays masked. Closing, switching entries,
searching/refreshing, or locking clears and closes the password display.

## Recent vault locations

**Recent Vaults** remembers the last 20 successfully created or unlocked vaults
on this device, newest first, with full paths. Open a selected vault or
double-click its location, then authenticate normally. Unavailable locations
stay listed so removable or network drives can be reconnected. **Forget selected**
removes only the history entry, never the vault. Locations are stored in an
owner-only file at `$XDG_DATA_HOME/vanwormai-vault/recent-vaults.json` (normally
`~/.local/share/vanwormai-vault/recent-vaults.json`). Passwords and entries are
not included. History is local to each device and is not synced.

Sync inspects and builds encrypted SQLite snapshots locally. The shared folder is used only for file transfers, lock directories, and atomic replacement; SQLite does not open databases on the share. The share must support those filesystem operations.

### Resolve sync differences

When both copies changed or a new device is not paired, Sync Now opens an in-app comparison after requesting the shared vault’s master/fallback password. Select each row to compare description, link, username, notes, and masked passwords. Password differences are flagged; revealing is an explicit checkbox inside the app. Choose Local, Shared, or Omit for every differing entry, or use all entries from one copy. An absent-side choice removes that entry from the result. Entries with different IDs remain separate even if their descriptions match.

Apply confirms the operation, checks that neither copy changed during review, and keeps encrypted `.conflict-*.sqlite` safety backups of both originals. These backups are not automatically pruned. The resolved result uses the shared vault’s encryption and password/YubiKey settings so a separately created desktop vault can join it. Both files receive the same result and the authenticated local session stays open. If a transfer fails midway, keep the safety backups and both copies; file replacement across two devices is not one atomic transaction. There is no three-way deletion inference: missing entries require explicit review. Cancelling leaves both vaults unchanged.

### Lock settings

Lock Settings sets a per-device inactivity timeout from 1 to 10080 minutes, with a five-minute default. Zero is Unlimited and requires acknowledging a warning. Unlimited disables automatic locking; manual Lock and closing the app still clear the session. Keyboard, mouse clicks and scrolling restart the inactivity timer. Preferences contain no passwords and are not synced. Sync, conflict resolution, shared-folder selection, password/key changes and authenticated restore keep the session open. Selecting the already-open vault also leaves it open; switching to a different local vault requires authentication. Failed validation still locks the session when needed.

### Automatic sync

Sync Settings enables background sync by default for configured vaults, with an interval of 30 seconds (select 5–86400 seconds). Sync runs at startup, on the interval, after entry edits, and before normal closing, including while locked. It never unlocks a vault by itself. Locked transfers use encrypted files without a data key; SQLite envelopes are checked and authenticated contents are verified when you unlock. Downloads preserve the locked state. When already unlocked, incoming entries are authenticated before replacement. Disabling automatic sync also disables its startup and closing runs; Sync Now remains available. NAS mounting and VPN connection are handled by the user.

Network operations run on encrypted local snapshots in a worker thread. Edits during uploads trigger another upload; edits during downloads stop replacement and preserve both copies for review. Results wait until open dialogs close. Shared-folder changes, local-vault switching and manual Sync Now wait for the current worker. Conflicts and unavailable shares appear in the sync status without recurring popups. Click Sync Now for conflict review. Close waits for its final sync attempt; errors warn that the local copy is saved. A crash, forced exit, unavailable NAS can leave changes unsynced.

Remote changes normally arrive within the receiving device’s polling interval when both apps are running and connected; edits are uploaded immediately after saving. Devices editing simultaneously can still require explicit conflict resolution. Background success does not reset the inactivity-lock timer. No-change polls create no retained backups. Automatic backup limits still apply.

The running version is shown in the window title and below the app heading. If Sync Settings says sync runs only when clicking Sync Now, close that older app and install the current release.

### Entry-level automatic merging
After a successful sync, each device remembers one baseline containing entry IDs and SHA-256 fingerprints of encrypted payloads, plus the authentication-metadata fingerprint. No readable passwords, descriptions or notes are stored in this history. Independent additions, edits and deletions merge automatically, including while locked. Competing edits to one entry, delete-versus-edit, differing authentication settings, or missing history require explicit review. Independent choices are preselected in the comparison so only unresolved entries need a decision.

Existing devices establish this history on their next successful sync; divergent copies with no history must first be reconciled manually. Do not copy the device-local .sync.json file between devices. Backups retain both original copies before a merge and use the configured retention limit. Shared and local replacement are separate operations; an interrupted transfer can need a retry or review. Concurrent local edits during the background merge are preserved and prevent local replacement. Update all participating devices to 0.1.14 for consistent merging behavior.

### Copy individual fields
Select an entry and use Copy Field to copy Description, Link, User Name, Password or Notes. Each masked password row also has a Copy button. Add/Edit windows provide Copy beside each field, using the current unsaved text. Copying does not reveal passwords. All app copy buttons restart the 30-second clipboard timer and clear on lock; later clipboard content from other applications is left alone.
