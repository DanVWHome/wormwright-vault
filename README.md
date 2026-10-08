# Wormwright Vault

An offline password and code manager by Dan Van Wormer with AI assistance.
Keep an encrypted local vault on each computer and synchronize through a
network folder you control. Use Vault alone for one user on one or several
devices. The optional Vault Manager handles separate users, groups, exclusions,
recovery and administration within one shared vault.

## Linux Mint release: 0.3.1

Supports **Linux Mint 22.x on Intel/AMD 64-bit computers (amd64)**, with glibc
2.39 or newer. Cinnamon and XFCE are the intended desktop environments.
Other distributions, earlier Mint versions, ARM, Windows, macOS and mobile apps
are not included in the current support claim.

[Download the release](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.1)
without a GitHub account. Choose `wormwright-vault-mint_0.3.1_amd64.deb` in Assets.
Make an encrypted backup and close both apps before installing:

```bash
sudo apt install ~/Downloads/wormwright-vault-mint_0.3.1_amd64.deb
```

Open **Wormwright Vault** or **Wormwright Vault Manager** from the application menu.
The package replaces the managed beta and retains current-format vault files,
credentials, remembered locations and sync settings. Existing beta launcher
commands remain aliases. No conversion or move of working vaults occurs.
The older personal prototype is a separate package.

See [installation and upgrade details](docs/MINT-RELEASE.md). New users receive
an introduction screen; the bundled synthetic demo is an explicit optional choice.
Searchable Help and the offline narrated tutorial are available in both apps.
The tutorial was recorded against 0.2.13; Help describes current behavior.

## Features

- Encrypted passwords, PINs, recovery codes, combinations and notes; links optional.
- Search description, link and notes; sortable non-secret fields, random password
  generation, duplicate-password indicators, per-field copy and large display.
- Adjustable inactivity lock and clipboard clearing after 30 seconds.
- Separate account passwords and optional YubiKey PIN/touch authentication.
- Encrypted per-entry keys and signed access policies; group sharing with
  individual exclusions and Manager recovery authority.
- Soft deletion, red deleted markers, deleted-only filtering and Manager restore.
- Encrypted backups/database export and freshly authenticated plaintext CSV export.
- Automatic sync on startup/unlock, after edits, periodically and on normal close,
  including encrypted transfers while locked when the app is running.
- Independent-entry merging; competing edits require explicit resolution.
- Configurable retained backup limits; Manager emergency lockdown.
- Two coordinated app views sharing one session and local UI-only AI hooks.

## Shared-folder sync

Every device works on a local file. Configure the same dedicated mounted NAS
folder under **Settings → Sync Settings**. Compatible SMB or FTP mounts can be
used; a VPN/Twingate can provide access to the network. The shared folder must
support the required lock-directory, transfer and replacement operations.
Do not open the shared master directly or use a cloud-mirrored folder.
For another device, export/copy the same encrypted vault, keep it locally and
configure the same shared folder. Device sync settings/history stay device-local.
Help includes setup, new-user provisioning and lost-database recovery walkthroughs.

Offline edits remain local until a successful sync. Revocation and lockdown
cannot erase passwords already known or contained in disconnected copies or old
backups. The Manager can access all entries and recover accounts. NAS permissions
are separate from encrypted entry access. CSV exports contain readable passwords.

## AI lookup

For an explicit working vault path:

```bash
wormwright-control-mint lookup Gmail --vault /path/to/local.sqlite
wormwright-control-mint open --vault /path/to/local.sqlite
wormwright-control-mint lock --vault /path/to/local.sqlite
```

Hooks select masked results or present authentication. They return only
acknowledgments, never passwords or records. The user chooses whether to show or
copy a value. Run the GUI in the normal desktop session for physical key access.
See [the hook contract](docs/INTEGRATION.txt).

## Development and validation

Python 3.10+ is required for source development. Install the Qt display/FIDO
prerequisites and Python venv support as needed. The bundled installer does not
install Python packages at launch.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python tests/run_checks.py
.venv/bin/python packaging/build-mint.py --work-dir build/mint --output-dir dist
```

The full synthetic regression suite passes for 0.3.1, including storage, tamper
rejection, user isolation, authentication simulation, backups, exports, local IPC,
sync, merges, UI behavior and package staging. Reported device testing covered
three Linux computers, offline edits, conflicts, FTP and SMB. This is not an
independent security audit. See [validation scope](docs/VALIDATION.md) and
[multi-user design and limits](docs/MULTIUSER-DESIGN.md).

## Next platform

Android for **Pixel 10 running GrapheneOS** is next: account-password unlock,
offline operation and NAS sync without Google Play services. YubiKey is outside
the first Android build. No Android APK is available yet.
See [Android design](docs/ANDROID-DESIGN.md) and [roadmap](docs/ROADMAP.md).

## Repository boundary and licensing

Only source, documentation, packaging, branding and explicitly synthetic demo
fixtures belong in Git. Real databases, CSV exports, backups, credentials,
signing keys and build environments must remain excluded. Installer artifacts
are published separately as release assets. Do not attach real data to bug reports.

No application license has been selected; public visibility does not grant an
open-source license. Third-party licenses apply to bundled dependencies, and
notices are included in the package. Approved mascot references are in assets.


## Android preview

An Android preview is available for manual APK installation, tested on Pixel 10 with GrapheneOS. It imports an encrypted format-2 vault and supports offline editing and direct SMB NAS sync. See [Android setup](android/README.md). Desktop 0.3.1 adds username search.
