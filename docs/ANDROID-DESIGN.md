# Android first build: Pixel 10 / GrapheneOS

Status: design and acceptance criteria, not an available APK.

## Confirmed scope

Use the existing vault account password. YubiKey is not required or included in
this first mobile build. Google Play services are not required. The main Vault
app is the initial mobile interface; Manager administration can stay on Linux.
The phone should eventually read, create, edit and soft-delete permitted entries
using the same current-format vault and common NAS master as Linux.

## Build sequence

1. Establish an Android build and signing process with a separate test app ID.
   Preserve the signing key privately for future APK upgrades. Do not commit it.
2. Verify native crypto interoperability with exported synthetic Linux vaults.
   Match Argon2id parameters, SecretBox, SealedBox, Ed25519 signatures, canonical
   JSON serialization, account-name normalization and signed access policies.
   Tampered or unsupported files must fail closed before entries reach the UI.
3. Implement private local storage, explicit database import, account unlock,
   search, masked list, copy with clearing, large display, auto-lock and editing.
   Exclude working files and secrets from Android cloud/device backup and logs.
   Clear visible secrets on backgrounding and block password-screen screenshots.
   Account names are needed only for multi-user vaults; obey group/exclusion rules.
4. Add direct SMB sync against a dedicated *synthetic* NAS share. Android does
   not provide the same GVFS filesystem mount as Mint. Reproduce the same shared
   lock directory, snapshot validation, entry merge, retained backups and atomic
   replacement protocol. Do not bypass an administrative conflict or overwrite
   a changed copy. Add FTP only when required remote operations are verified.
5. Sync on foreground/unlock/save and provide an explicit Sync Now control.
   Poll while the app is open. Standard Android periodic work has a 15-minute
   minimum and may be delayed; do not promise 30-second closed-app sync. Avoid
   an always-running foreground service unless the user chooses that tradeoff.
6. Test password resets, disabled accounts, exclusions, offline edits,
   interrupted uploads, simultaneous edits and recovery using dummy data before
   allowing mobile write access to the real shared vault.

## Distribution

Begin with a signed test APK downloadable from GitHub, independent of the Play
Store. The first device acceptance test is the user's Pixel 10 / GrapheneOS.
NAS credentials should be protected by Android Keystore-backed storage, separate
from the portable vault. VPN/Twingate access remains the phone's network setup.

## Sources

- [Android periodic work constraints](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [GrapheneOS supported devices](https://grapheneos.org/faq#supported-devices)

The mobile app is a native implementation and interoperability effort, rather
than repackaging the desktop Qt binary. Android backup, clipboard and lifecycle
behavior require device tests; Linux tests alone cannot validate them.
