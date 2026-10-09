# Submission-chat handoff — pending device acceptance

Publisher: Dan Van Wormer; support: danvanwormer@pm.me.
App: Wormwright Pocket Vault, version 0.1.0-test.1/versionCode 1.
Package: ai.wormwright.vault.standalone (permanent). Existing companion:
ai.wormwright.vault.preview. Distinct vector phone/coral-worm icon is in
app/src/main/res/drawable/pocket_icon.xml. There are no content providers, shared
user IDs, companion paths/aliases, storage permissions or NAS connection settings.
Only USE_BIOMETRIC is declared; no Internet permission. Application sandbox and
Keystore aliases separate it from the companion. Installation identifiers were
checked statically; actual coexistence/update/uninstall testing remains pending.

Development branch: feature/android-standalone in DanVWHome/wormwright-vault.
A draft test release and draft PR are prepared; links are provided in the chat.
Public release publication requires explicit device-test confirmation. Current
behavior, dependencies, key design, backup retention/deletion and complete desktop
migration steps are documented in README.md; device acceptance in DEVICE-TESTS.md.
Release notes/checksums/native verification accompany the installable APK. Existing
desktop/companion directories are unchanged; copied encryption engine matches src.

Validation passed: six offline Python tests; desktop account management and existing
companion pair/edit/upload plus desktop download against a simulated shared folder;
API-36 APK and AAB builds; Android lint; APK signature; 16 KiB ZIP/ELF checks for 138
libraries including Python assets. The fresh-install recovery test uses a new random
local secret and does not require the original device key. It is an engine test,
not a real second-phone installation. Android authentication cancellation/failure,
lifecycle/clipboard behavior, key invalidation, app coexistence and real SMB NAS
end-to-end migration are device acceptance work. No personal vault data was accessed.

Production readiness remains conditional:

- Complete DEVICE-TESTS.md, including actual desktop UI, test SMB share and existing
  companion Android workflow with invented data. Fix any device-specific failures.
- Decide and configure publisher-controlled Play App Signing and separate upload
  credentials; back them up privately. The dedicated test key is outside Git and
  must not become the production key by accident. The release AAB is unsigned until
  configured; it is a packaging proof, not upload-ready. Production versionCode
  must increase; changing signing identity requires an encrypted backup/reinstall.
- Verify release-signed AAB/APK and run on a 16 KiB device/emulator. Static checks
  alone do not confirm runtime support. Confirm Play's native-library report.
- Confirm target requirements at actual submission date (currently API 36), Play
  account verification and any account-specific testing prerequisites in Console.
- Complete the separate submission documents, Data safety, privacy policy, store
  listing/screenshots/content rating and GPL/third-party distribution notices.
  No server data collection is implemented; document-provider behavior is chosen
  by the user. No broad storage permission, account service or special access.
- Publish the test release only after Dan's confirmation. Do not submit to Play
  from this chat. Full security review is still advisable before real-secret use.

Compatibility: actual format-2 personal Owner account, signed policy and recipient
keys; migration rewraps Owner credentials on a copy, not the phone secret. Desktop
Manager may provision additional accounts/groups later; once managed, Owner login
must be explicit. Current fields and deleted tombstones transfer. Format 2 has no
per-entry edit history. Standalone restores reject managed vaults; the companion
retains that role. Portable backups and migration exports share a format but use
separately chosen secrets and have distinct labels/workflows.
