# Wormwright Vault

An offline Linux password-vault prototype by Dan Van Wormer with AI assistance.
Built for Linux Mint Cinnamon and XFCE. Entry passwords and metadata are
locally encrypted; optional YubiKey PIN plus touch and a separate password
fallback unlock the vault.

## Install the prototype

The supplied `wormwright-vault_0.1.3_amd64.deb` targets **Linux Mint 22.x on
Intel/AMD 64-bit computers** (glibc 2.39 or newer). It bundles Python, Qt,
and encryption libraries. It does not download Python packages at launch.
APT may download the Linux display and FIDO-permission prerequisites during
installation. Mint 21 needs a build made on its older base; this particular
binary is not claimed compatible with it.

```sh
sudo apt install ./wormwright-vault_0.1.3_amd64.deb
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
A download locks the app; unlock using the credentials in the updated copy.
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
