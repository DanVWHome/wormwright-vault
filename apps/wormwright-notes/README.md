# Wormwright Notes — 0.1.0-preview.3

Offline Android notes and checklists with autosave, search, pins, Trash, sharing and manual NAS backups. No ads, purchases, analytics or app account. Ordinary notes require Android 8 or later; secret notes require Android 11 or later with a secure phone screen lock.

## Notes and checklists

Tap **+ New note**, then **Note** or **Checklist**. Changes save automatically on the phone. Use **Options** to pin, share, change between plain text and a checklist, or move a note to Trash. Use **More → Open trash** to restore or permanently delete a note.

## Secret notes

Open a note or checklist and choose **Options → Make secret**, then confirm with Android's system phone PIN, pattern or password prompt. The app does not receive or store that credential. The list shows only “Secret note”; the title and contents are hidden, including in Trash, and are excluded from search.

Tap a secret note and enter the phone screen lock to read or edit it. **Share text** works after unlocking and sends ordinary text to the app you choose. Returning to the list, sharing into another app, backgrounding or recreating the activity locks the secret again. **Options → Lock now** locks it immediately. **Make public** removes protection after confirmation while the note is unlocked.

Secret title/content is encrypted in the app database using a phone-bound Android Keystore AES-GCM key. Secret editor screenshots and recent-app previews are protected; its text fields disable view-state saving, autofill and personalized keyboard learning. Previously exported plain-text backups remain unchanged when a note becomes secret.

## Backups

**More → Back up all notes** saves a backup through Android's file picker. **More → Restore backup** adds its notes; restoring the same file twice creates duplicates. Import and export are limited to 20 MB.

- Without secret notes, backups remain ordinary JSON, compatible with earlier Notes versions.
- If any secret notes exist, including in Trash, backup requires phone authentication and a separate backup password of at least 12 characters. The entire `.wwnotes` backup is encrypted, including public notes and secret flags.
- Restore a `.wwnotes` file using its backup password. If it contains secret notes, confirm the receiving phone's screen lock; restored secrets remain locked and are encrypted with that phone's key.

Keep the backup password separately. Your phone PIN cannot recover a protected backup on a replacement phone. Uninstalling removes the local notes and phone key; a usable protected backup and its separate password are required for recovery.

## Your NAS

Open **More → NAS settings**, enter the NAS username/password once, then **More → Save backup to NAS**. Defaults match the earlier Vault connection: address `192.168.1.144`, share `share`, folder `PasswordVault/Dans-Vault`. The folder must exist and the NAS account needs read/write access. On GrapheneOS, allow Network permission for NAS access.

Each snapshot gets a unique dated filename, is uploaded over signed SMB, read back for verification, and then published. Ordinary backups use `.json`; protected backups use `.wwnotes`. This is manual backup, not automatic synchronization. Vault files are never opened or changed. Download a NAS snapshot with a file manager, then use **Restore backup**.

Saved NAS credentials are separately encrypted on this phone and excluded from all note backups. Notes cannot read Vault's stored credentials.

## Install or update

Download `Wormwright-Notes-0.1.0-preview.3.apk` from [the Notes page](https://wormwright.com/notes.html), open it on your phone and approve installation. Back up notes first, then install over the existing app. The package and signing identity match previews 1 and 2. Do not uninstall to update.

The app upgrades its database in place while preserving existing notes, checklists, pins and Trash. User reports confirmed preview 2 working, including sharing and NAS backups. The new secret flow still needs verification on the user's phone; automated regression results are recorded with the release.

## Build and tests

Java 17, Android platform 35 and build-tools 35.0.0 are required. Open this project in Android Studio, or set `ANDROID_SDK_ROOT` and run `build-preview.sh`. The standalone build uses the included third-party library JARs. Preserve the generated preview signing key for in-place updates; `SIGNING_KEY` selects the existing compatible key.

With Gradle 8.13, run `gradle testDebugUnitTest` for encryption, backup integrity, database migration, privacy, relocking and sharing regressions. `assembleDebugAndroidTest` builds the disposable-emulator PIN test; `.github/workflows/android-notes-privacy.yml` in the parent repository runs it. The older `tests/NasBackupTest.java` checks NAS paths and incomplete/corrupt uploads.

See LICENSE, LICENSING.md, THIRD-PARTY-NOTICES.txt and licenses/. Application code is GNU GPLv3 only; Wormwright branding is separate.
