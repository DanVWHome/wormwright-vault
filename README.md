# VanWormAI Vault

An offline Linux password-vault prototype by Dan Van Wormer with AI assistance.
Built for Linux Mint Cinnamon and XFCE. Entry passwords and metadata are
locally encrypted; optional YubiKey PIN plus touch and a separate password
fallback unlock the vault.

## Install the prototype

The supplied `vanwormai-vault_0.1.0_amd64.deb` targets **Linux Mint 22.x on
Intel/AMD 64-bit computers** (glibc 2.39 or newer). It bundles Python, Qt,
and encryption libraries. It does not download Python packages at launch.
APT may download the Linux display and FIDO-permission prerequisites during
installation. Mint 21 needs a build made on its older base; this particular
binary is not claimed compatible with it.

```sh
sudo apt install ./vanwormai-vault_0.1.0_amd64.deb
```

Open **VanWormAI Vault** from the application menu. If the key is not detected
immediately after installation, unplug and reconnect it to apply the installed
FIDO device permissions. Run the app as your normal user.

Existing prototype vaults under `~/.local/share/atlas-portable` are reused.
New vaults default to `~/.local/share/vanwormai-vault`. Installing or removing
the package does not import, replace, or delete a user's vault.

## Assistant lookup

```sh
vanwormai-control lookup Gmail
vanwormai-control open
vanwormai-control lock
```

These commands select masked entries or show the unlock screen. They return
only acknowledgments, not passwords, records, or match counts.

An assistant-launched subprocess can inherit the assistant's USB restrictions.
For voice requests to start the GUI in your ordinary desktop session, enable
this **optional** fixed-action launcher from your own terminal after installing:

```sh
vanwormai-enable-desktop-launcher
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

This remains a prototype. Synchronization and forgotten-password recovery
are not implemented. Physical YubiKey enrollment/unlock and installer behavior
must be checked on each target laptop/desktop before using real credentials.
No application license has been selected; keep the repository private for now.
Third-party component licenses remain applicable to bundled dependencies.
