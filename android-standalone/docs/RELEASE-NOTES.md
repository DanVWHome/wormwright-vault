# Wormwright Pocket 0.1.0-test.5 — device testing draft

Your personal password vault. Standalone offline Android app by Dan Van Wormer.

Test.5 fixes immediate list refresh after deleting and restoring entries. Commands
which return no value now complete normally, so the list refresh is always run.

Test.4 fixes the editor crash reported on test.3. Delayed record-dismiss callbacks
cannot clear a newer editor, and editor/password callbacks reference their own
window. Opening a vault or sample now immediately shows an indeterminate spinner
and “Opening vault…”. Repeat opening attempts are blocked while work is underway;
completion, errors and locking clear the indicator without stale callbacks hiding
newer work. Camera spacing, grouped record controls and the approved icon remain.

Package and dedicated test signing identity are unchanged. Export a portable
backup, then install over the earlier test build without uninstalling. VersionCode
is 5. The NAS companion receives the same opening feedback in preview.5. Real
Android message-loop tests cover repeated record/edit/save/cancel transitions,
visible opening feedback, error cleanup and stale completion after locking.
Physical biometric/PIN and actual SMB NAS acceptance remain separate checks.

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
  desktop code is unchanged. The NAS companion gets loading feedback separately. No network permission or NAS
  libraries, analytics, advertising, cloud services or generative AI features.
- Target API 36; APK/native-library static alignment checks passed for 16 KiB pages.

This is a **debuggable test APK**, signed with a persistent dedicated Pocket test
identity, not the production upload/app-signing key. Use invented data until device
acceptance passes. Keep portable backups before changing signing identity.

Automated validation: six offline engine tests, including fresh-key restoration,
wrong secrets, corruption, crypto password wrapping, CRUD/lock/sample isolation,
and a real desktop/companion engine migration round trip with a simulated shared
folder. Android compilation and lint passed. APK signature and all 138 nested ELF
libraries were checked. Desktop sources and crypto engine were not changed. The companion
receives loading feedback in preview.5. Physical biometric/PIN fallback, coinstallation/update/uninstall retention,
16 KiB runtime and actual desktop UI + SMB NAS + companion device workflow remain
pending. Automated protocol checks do not replace those device tests.

See README.md for installation/recovery/migration instructions and DEVICE-TESTS.md
for acceptance. This release stays **draft** until Dan confirms device testing
passed. No Google Play submission is authorized here.

Support: danvanwormer@pm.me. Do not include personal vaults or credentials in reports.
