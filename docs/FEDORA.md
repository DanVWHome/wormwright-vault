# Fedora 44 preview — Wormwright Vault 0.3.8

For Fedora Workstation or KDE on x86_64 (Intel/AMD 64-bit PCs).
Targets Fedora 44. This is a preview, not a package in the official Fedora repositories.

Install the downloaded package from its folder:

```sh
sudo dnf install ./wormwright-vault-0.3.8-1.fc44.x86_64.rpm
```

Open Wormwright Vault or Wormwright Vault Manager from the applications menu.
In NAS Sync Settings, click Choose shared folder, select the connected NAS by
name, then choose the dedicated vault folder. No mount path needs to be typed.
If the NAS is not listed, connect it in Files and click Refresh.
The package includes Python and Qt; DNF installs required system libraries and
security-key permissions. Reconnect your YubiKey after installation.

Keep a local working vault and sync through an SMB share using Files. Use a
synthetic vault for the first Fedora test. Existing vault formats are unchanged.
The RPM installs application files only; it does not move or delete user vaults.
Remove the application with `sudo dnf remove wormwright-vault`.

This is a preview built on Linux Mint 22.3 with a glibc 2.39 baseline. Package
structure, bundled runtime and synthetic checks are tested locally. Fedora
installation, Wayland/X11 desktop startup, real YubiKey and SMB sync still need
on-device verification. Fedora Atomic desktops and ARM are not validated.

Rebuild with Python dependencies from requirements-build.txt, RPM build tools,
and `python packaging/build-fedora.py --work-dir /tmp/ww-build --output-dir dist`.
The builder uses an explicit source/assets allowlist and disables RPM stripping
and automatic dependency export for private bundled libraries. Runtime system
dependencies are declared explicitly.

Open Existing Vault also lists connected NAS shares by name, with a Browse other folders option for local vaults.

Local control sockets use a short private path on this computer, including when opening a long NAS vault path.

Selecting an existing NAS master automatically creates or reuses a private local working copy and links it to that NAS folder. Opening it again preserves the sync settings and local edits.

## Tutorial and updates

Help → Watch Tutorial includes the re-recorded 7 minute 44 second desktop walkthrough. Help → Wormwright Website opens wormwright.com. There is no Wormwright Fedora software repository yet: download later RPM releases from the Linux webpage and install over the existing version with DNF. User vaults and local preferences are retained. The Mint APT repository is for Mint only.

## Verification and troubleshooting

Compare the RPM SHA-256 against SHA256SUMS on the same GitHub release. This preview RPM is unsigned; the checksum detects a damaged download but is not a publisher signature. Download only from the linked Wormwright GitHub release. If the graphical installer hangs or reports a transaction error, close it and use the DNF installation command above.

The first-run introduction lets you create a vault, open an existing one, or explicitly load the disposable demo. One user across multiple devices needs only Vault. Use Manager for users, groups and exclusions. Each device needs a local working copy of the same encrypted vault and the same dedicated shared folder. Local storage need not be a dedicated folder; the shared sync folder should be dedicated to one vault.

Validate startup in your desktop session, tutorial sound/video, YubiKey if used, NAS reconnect/restart, sync in both directions, and offline edits with a disposable vault before relying on the preview. Revocation and permission changes arrive after successful sync and cannot recall secrets already retained offline.
