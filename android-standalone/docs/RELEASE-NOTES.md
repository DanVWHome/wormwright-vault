# Wormwright Pocket 0.1.0-test.3 — device testing draft

Your personal password vault. Standalone offline Android app by Dan Van Wormer.

This update fixes the camera/status-bar overlap by respecting system-bar, display
cutout and keyboard insets on every main screen, in portrait and landscape. The
record dialog now uses its description as the title, shows username, website,
masked password and notes together, and groups all action buttons below the fields.
Show/Hide password toggles like the NAS companion. Copying each field remains
available. Dialog contents are cleared when closed. VersionCode is now 3.

The package and dedicated test signing identity are unchanged. Export a portable
backup, then install over test.1 or test.2 without uninstalling. Dan confirmed
test.2 downloaded and installed; physical cutout and layout verification of this
update remains pending.

- Create a personal encrypted vault protected by phone authentication through an
  authentication-per-operation Android Keystore key. Optional separate vault
  password adds an Argon2id/SecretBox cryptographic layer.
- Add, edit, delete, restore, search, view and copy descriptions, usernames,
  passwords, links and notes. Separate invented sample vault.
- Lock on leaving the app and after two idle minutes; clear copied secrets after
  30 seconds or on lock. Screenshot protection includes sensitive dialogs.
- Export/restore encrypted backups using a separate password or generated recovery
  key, independent of the original phone. Recovery requires an exported file and
  its secret; phone authentication cannot recover backups on a replacement device.
- Export real signed format-2 desktop/NAS migration vaults, with a chosen master
  password and existing Owner identity. Preserve entry fields and deleted entries.
- Distinct app name/icon and package `ai.wormwright.vault.standalone`; existing
  desktop and Android companion code is unchanged. No network permission or NAS
  libraries, analytics, advertising, cloud services or generative AI features.
- Target API 36; APK/native-library static alignment checks passed for 16 KiB pages.

This is a **debuggable test APK**, signed with a persistent dedicated Pocket test
identity, not the production upload/app-signing key. Use invented data until device
acceptance passes. Keep portable backups before changing signing identity.

Automated validation: six offline engine tests, including fresh-key restoration,
wrong secrets, corruption, crypto password wrapping, CRUD/lock/sample isolation,
and a real desktop/companion engine migration round trip with a simulated shared
folder. Android compilation and lint passed. APK signature and all 138 nested ELF
libraries were checked. Desktop/companion source files and crypto engine were not
changed. Physical biometric/PIN fallback, coinstallation/update/uninstall retention,
16 KiB runtime and actual desktop UI + SMB NAS + companion device workflow remain
pending. Automated protocol checks do not replace those device tests.

See README.md for installation/recovery/migration instructions and DEVICE-TESTS.md
for acceptance. This release stays **draft** until Dan confirms device testing
passed. No Google Play submission is authorized here.

Support: danvanwormer@pm.me. Do not include personal vaults or credentials in reports.
