# Wormwright Vault

An offline encrypted password and code manager by Dan Van Wormer with AI assistance.
Keep a local working vault on each device and sync through your own NAS.

## Downloads

- [Linux Mint 0.3.2 — stable](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.2)
- [Linux NAS lock-fix preview](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.2-lockfix-preview.1)
- [Windows 0.3.2 preview 2](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.2-windows-preview.2)
- [Android 0.1.0-preview.3](https://github.com/DanVWHome/wormwright-vault/releases/tag/v0.3.1)

For setup and platform limits, see [the website](https://wormwright.com/vault.html),
[Windows setup](docs/WINDOWS.md), [Linux setup](docs/MINT-RELEASE.md), and
[Android setup](android/README.md). Windows includes Vault and optional Manager.
Extract the whole portable ZIP into a local folder; no Python installation is needed.

The Windows preview has been tested on one Windows laptop: password and enrolled
YubiKey unlock, remembered vault and sync settings, and window sizing worked.
Other Windows machines and all NAS scenarios have not been verified.

## NAS sync and compatibility

Use **SMB**. FTP-mounted shares have shown intermittent sync failures and incorrect
file-lock messages; switching the affected computer to SMB resolved that failure.
Keep each device’s local working copy separate from the shared master.
Windows preserves the existing Linux and Android vault formats and NAS sync
protocol. It does not require a vault-format migration or re-enrolling an
existing YubiKey. Android retains its existing preview feature limits.

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
