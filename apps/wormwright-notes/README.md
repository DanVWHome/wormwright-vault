# Wormwright Notes — 0.1.0-preview.2

An Android notes app with no ads, purchases, analytics, or app account. Requires Android 8 or later.

## Using the app

- Tap **+ New note**, then choose **Note** or **Checklist**.
- Changes save automatically on the phone. Notes work offline.
- Use **Options** inside a note to pin it, share text, change between checklist and plain text, or move it to Trash.
- Use **More → Open trash** to restore a note or permanently delete it.
- Search finds words in note titles and content.

## Backups and your NAS

**More → Back up all notes** saves a JSON file through Android's file picker. **Restore backup** adds notes from one of these files. Restoring the same file twice creates duplicates. Import accepts files up to 20 MB.

For direct NAS backups, open **More → NAS settings**. Connection defaults match the earlier Wormwright Vault Android setup:

- Address: `192.168.1.144`
- Share: `share`
- Folder: `PasswordVault/Dans-Vault`

Enter your NAS username and password once. Notes cannot read the credentials stored inside Vault. Notes encrypts its own saved NAS credentials using Android Keystore; these credentials are excluded from note backups.

Choose **More → Save backup to NAS** to create a dated JSON snapshot. Uploads require SMB signing, use a new filename, and verify the saved bytes before publishing the completed backup. The folder must already exist and your NAS account needs read/write access. Vault files are never opened or changed. This is manual backup, not automatic synchronization. To restore a NAS snapshot, download it using your file manager, then choose **Restore backup**.

Notes and exported backups are plain text, not encrypted vaults. Uninstalling the app removes its local notes; keep a separate backup.

## Installing this preview

Copy `Wormwright-Notes-0.1.0-preview.2.apk` to your phone and open it. Android may ask you to allow installation from the file app you used. This update uses the same package and preview signing certificate as preview 1. Install it over the existing app to retain your notes. The launcher now uses the larger checklist-and-pencil icon selected by the user. Back up your notes before updating; do not uninstall the app.

## Build and verification

The app compiled against Android API 35. The APK signature and package contents were checked. Ten host-side checks cover NAS path validation and rejection of truncated, oversized, or corrupted backup uploads. Phone interaction and an actual NAS connection have not yet been tested.

Open this folder in Android Studio to build it, or use `build-preview.sh` with Java 17, Python 3, Android platform 35, and build-tools 35.0.0. Set `ANDROID_SDK_ROOT` first. The script generates a preview signing key in its build directory; preserve it for updates. `SIGNING_KEY` can select an existing compatible key. Included library JARs make the standalone build possible without downloading dependencies.

Third-party libraries: SMBJ 0.14.0, asn-one 0.6.0, Bouncy Castle 1.79, MBassador 1.3.0, SLF4J API/NOP 2.0.9. See THIRD-PARTY-NOTICES.txt and library license files.

## Source and license

Application code is GNU GPLv3 only; see LICENSE and LICENSING.md. Matching source is included with each release. Wormwright branding is separate.
