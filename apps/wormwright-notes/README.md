# Wormwright Notes — 0.1.0-preview.5

Offline Android notes and checklists with autosave, search, pins, Trash, sharing and manual NAS backups. No ads, purchases, analytics or app account. Ordinary notes require Android 8 or later; secret notes require Android 11 or later with a secure phone screen lock.

## Notes and checklists

Tap **+ New note**, then **Note** or **Checklist**. Changes save automatically on the phone. Use **Options** to pin, share, change between plain text and a checklist, or move a note to Trash. Use **More → Open trash** to restore or permanently delete a note.

## Secret notes

Open a note or checklist and choose **Options → Make secret**, then confirm with Android's system phone PIN, pattern or password prompt. The app does not receive or store that credential. The list shows only “Secret note”; the title and contents are hidden, including in Trash, and are excluded from search.

Tap a secret note and enter the phone screen lock to read or edit it. **Share text** works after unlocking and sends ordinary text to the app you choose. Returning to the list, sharing into another app, backgrounding or recreating the activity locks the secret again. **Options → Lock now** locks it immediately. **Make public** removes protection after confirmation while the note is unlocked.

Secret title/content is encrypted in the app database using a phone-bound Android Keystore AES-GCM key. Secret editor screenshots and recent-app previews are protected; its text fields disable view-state saving, autofill and personalized keyboard learning. Previously exported plain-text backups remain unchanged when a note becomes secret.

## Backups

**More → Back up all notes** saves a backup through Android's file picker. **More → Restore backup** adds its notes; restoring the same file twice creates duplicates. Import and export are limited to 20 MB.

- Choose **Password** to protect a backup with a separate password of at least 12 characters. Existing password-protected backups remain supported.
- Choose **YubiKey** to protect it for all currently registered keys. Authenticate with one of those keys using its FIDO2 PIN and USB-C or NFC. Any of the included keys independently restores that same file on another phone.
- **Plain JSON** is available only when no secret notes exist. Public JSON remains compatible with previous Notes versions.
- Backups containing any secret notes, including Trash, encrypt the entire `.wwnotes` file. Password and YubiKey backup/restore do not add a phone-PIN prompt. Opening individual secret notes still requires the phone screen lock.
- Restore a `.wwnotes` file using its password or an included YubiKey, depending on how it was created. Secret imports require a configured screen lock, without prompting for it during restore. Restored secrets remain locked until opened.

Keep the backup password separately. Your phone PIN cannot recover a protected backup on a replacement phone. Uninstalling removes the local notes and phone key; a usable protected backup and its separate password are required for recovery.

## Up to four backup YubiKeys

Open **More → YubiKey backup keys**, then **+ Register YubiKey**. Name each key. If keys are already registered, authenticate with one first to authorize the change. Use the new key’s existing FIDO2 PIN and follow the USB-C touch or NFC prompts. NFC registration uses two taps: create the credential, remove the key, then enter its PIN again and tap the same key to verify it. Nothing is saved until verification succeeds. This uses a fresh NFC connection and does not retry PIN failures automatically. Notes creates a separate credential and does not alter Vault credentials, reset the key, change its PIN, or write OTP slots. A physical key already registered in this list is rejected; use a different physical key for an independent spare.

Register up to four keys before making a YubiKey backup. Every new file includes all currently registered keys. Adding a key does not change older files: make a new backup to include it. Removing a registration affects future files only; older backups still accept their original keys. You can rename and remove keys from the management screen.

Restore on a replacement phone by selecting the backup file and using any included key. No prior phone registration or phone-specific encryption key is needed. After restoring, you may remember the authenticated public registrations for future backups on the new phone, subject to its four-key limit. Renaming/removing registrations requires an existing registered YubiKey, without an additional phone PIN. The phone stores no YubiKey PIN, hmac-secret output or private backup encryption key.

Password and YubiKey are separate backup choices. A password-only file still needs its password; a YubiKey-only file needs one of the keys included when it was created. Keep an independent spare key and verify it by restoring a test backup. The user confirmed on physical hardware that preview 5 successfully registered a YubiKey over NFC, created a YubiKey-protected backup, removed the key registration from the app, and saved a backup to NAS. Removing a registration leaves existing backup files unchanged.

## Your NAS

Open **More → NAS settings**, enter the NAS username/password once, then **More → Save backup to NAS**. Defaults match the earlier Vault connection: address `192.168.1.144`, share `share`, folder `PasswordVault/Dans-Vault`. The folder must exist and the NAS account needs read/write access. On GrapheneOS, allow Network permission for NAS access.

Each snapshot gets a unique dated filename, is uploaded over signed SMB, read back for verification, and then published. Ordinary backups use `.json`; protected backups use `.wwnotes`. This is manual backup, not automatic synchronization. Vault files are never opened or changed. Download a NAS snapshot with a file manager, then use **Restore backup**.

Saved NAS credentials are separately encrypted on this phone and excluded from all note backups. Notes cannot read Vault's stored credentials.

## Install or update

Download `Wormwright-Notes-0.1.0-preview.5.apk` from [the Notes page](https://wormwright.com/notes.html), open it on your phone and approve installation. Back up notes first, then install over the existing app. The package and signing identity match the earlier previews. Do not uninstall to update.

The app upgrades its database in place while preserving existing notes, checklists, pins and Trash. User reports confirmed preview 2 working, including sharing and NAS backups. The user reported preview 3 looks good. The user confirmed on physical hardware that preview 5 successfully registered a YubiKey over NFC, created a YubiKey-protected backup, removed the key registration from the app, and saved a backup to NAS. Automated regression results are recorded with the release. This user confirmation covers backup creation, not restoration.

## Build and tests

Java 17, Android platform 35 and build-tools 35.0.0 are required. Open this project in Android Studio, or set `ANDROID_SDK_ROOT` and run `build-preview.sh`. The standalone build uses the included third-party library JARs. Preserve the generated preview signing key for in-place updates; `SIGNING_KEY` selects the existing compatible key.

With Gradle 8.13, run `gradle testDebugUnitTest` for encryption, backup integrity, database migration, privacy, relocking and sharing regressions. `assembleDebugAndroidTest` builds the disposable-emulator PIN test; `.github/workflows/android-notes-privacy.yml` in the parent repository runs it. The older `tests/NasBackupTest.java` checks NAS paths and incomplete/corrupt uploads.

See LICENSE, LICENSING.md, THIRD-PARTY-NOTICES.txt and licenses/. Application code is GNU GPLv3 only; Wormwright branding is separate.
