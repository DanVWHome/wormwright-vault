# Wormwright Vault

An offline encrypted password and code manager by Dan Van Wormer with AI assistance.
Keep a local working vault on each device and sync through your own NAS.

## Downloads

- [Linux Mint 0.3.11 — stable](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.11)
- [Windows 0.3.11 — stable](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.11-windows)
- [Fedora 44 — 0.3.11 stable](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.11-fedora)
- [Android Network/NAS 0.1.0-preview.21](https://github.com/DanVWHome/wormwright-vault/releases/tag/android-v0.1.0-preview.21)
- [Android Pocket 0.1.0-test.21](https://github.com/DanVWHome/wormwright-vault/releases/tag/pocket-v0.1.0-test.21)

Both Android .21 apps passed user testing on Pixel 10 with GrapheneOS, including
the numeric keypad, letters/symbols toggle, USB-C and NFC. See
[device testing](docs/ANDROID-DEVICE-TESTING.md). Windows 0.3.11 is stable after user confirmation of update discovery, enrollment guidance and successful key registration. Fedora 0.3.11 is also stable after confirmation that both keys work with the mounted NAS vault; see [preview notes](docs/DESKTOP-PREVIEWS-0.3.11.md).

For setup and platform limits, see [the website](https://wormwright.com/vault.html),
[Windows setup](docs/WINDOWS.md), [Linux setup](docs/MINT-RELEASE.md), and
[Android setup](android/README.md). Windows includes Vault and optional Manager.
Extract the whole portable ZIP into a local folder; no Python installation is needed.

The Windows preview has been tested on one Windows laptop: password and enrolled
YubiKey unlock, remembered vault and sync settings, and window sizing worked.
Other Windows machines and all NAS scenarios have not been verified.

## Wormwright Notes for Android

A separate notes and checklist app, with offline autosave, search, pins, trash,
file backup/restore and manual SMB NAS backups. No ads or in-app purchases.

- [Download and install Wormwright Notes](https://wormwright.com/notes.html)
- [Notes preview 0.1.0-preview.2](https://github.com/DanVWHome/wormwright-vault/releases/tag/notes-v0.1.0-preview.2)
- [Notes source, build and backup instructions](apps/wormwright-notes/README.md)

This is a separate app; it does not open or modify Vault databases.

## NAS sync and compatibility

Use **SMB**. FTP-mounted shares have shown intermittent sync failures and incorrect
file-lock messages; switching the affected computer to SMB resolved that failure.
Keep each device’s local working copy separate from the shared master.
Windows preserves the existing Linux and Android vault formats and NAS sync
protocol. It does not require a vault-format migration or re-enrolling an
existing YubiKey. Android retains its existing preview feature limits.

The Linux preview also corrects an unsupported read/write reopen on GVFS SMB
mounts and verifies upload bytes before replacing the shared file.

The NAS cleanup improvements guarantee release attempts after scratch allocation
and cleanup failures, retry short-lived release failures, and report persistent
failures. They never clear another device’s existing lock automatically. The
intermittent NAS-lock issue still needs testing over time. Locked desktop apps
may continue automatic sync; fully exit other apps for an isolated test.

## Build and validation

GitHub Actions builds the Windows portable ZIP and Linux preview. Synthetic
checks cover encryption, signed FIDO2 assertions, sync/merge/conflict behavior,
settings retention, lock cleanup, backups, UI behavior and package startup.
See `.github/workflows/`, `packaging/`, and `tests/`. Hardware and real NAS tests
complement these automated checks.

## License and support

Application code is [GNU GPLv3 only](LICENSE). See [LICENSING.md](LICENSING.md)
for third-party notices and branding exclusions. Music and other Wormwright
projects are outside this software license.

[Report an ordinary bug](https://github.com/DanVWHome/wormwright-vault/issues/new?template=bug-report.yml).
For security issues, see [SECURITY.md](SECURITY.md). Never attach real vaults,
password exports, credentials, recovery codes or YubiKey PINs to public reports.
Only source, packaging, documentation, branding and synthetic fixtures belong
in this repository; real vaults, backups, credentials and signing keys do not.
