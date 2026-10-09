# Wormwright Pocket — Android standalone test

Your personal password vault.

Publisher: Dan Van Wormer. Support: danvanwormer@pm.me.
Permanent application ID: **ai.wormwright.vault.standalone**.
Coral Wormwright peeking out of a stitched blue pocket with a gold padlock. Minimum Android 11 (API 30),
target/compile Android 16 (API 36); arm64-v8a and x86_64. Test version 0.1.0-test.4.

This updates previous Pocket Vault and Wormwright Pocket test builds. Keep the app installed;
export a portable backup first, then install test.4 over it. The package and
dedicated test signing identity are unchanged.

Test.4 fixes the record-to-editor crash and shows a spinner while opening a vault.
Repeated opening attempts are blocked until work completes. Earlier fixes keep screens clear of the camera cutout, system bars and keyboard. Entry
details use the description as their title, show fields together and group action
buttons below them, with a Show/Hide password toggle.

## Installation and first test

Use invented data until the device checklist passes. Download the APK from the
Wormwright website, private draft release or local handoff folder, verify SHA-256 against SHA256SUMS,
transfer it to the phone, and allow your file manager to install this one APK.
Launch **Wormwright Pocket**, leaving **Wormwright Vault Preview** installed.
A secure device screen lock is required for personal-vault creation and access.
The sample vault contains invented accounts and is separate from personal data.

Create a vault, leave the optional vault-password fields blank for phone-only
access, then authenticate. Add descriptions, usernames, passwords, links and notes.
Search covers descriptions, usernames and links. Copy any field; password display
requires an explicit Reveal action. Edits save locally; deletes move entries to
Recently deleted, where they can be restored. No NAS, managed-account or group
administration appears in this app. No Internet permission, cloud connection,
analytics, ads or AI functionality is included. Android autofill is not implemented.

Leaving the activity locks the vault; reopening requires app-specific phone
authentication. The idle timeout is two minutes. The clipboard clears after 30
seconds or at locking, provided the current clipboard still matches this app's
copy. Activity and sensitive-dialog windows reject screenshots and recent-app
previews. Sample access is deliberately unauthenticated because its data is invented.

## Encryption and key lifecycle

The unmodified desktop format-2 engine encrypts entry fields with random keys,
sealed recipient envelopes and signed policy/entry documents. Its Argon2id master
credential is a random 384-bit local secret, not the phone PIN. The local secret
is wrapped with AES-256-GCM under a non-exportable Android Keystore key configured
for **authentication on each cryptographic operation**, permitting strong biometric
or device credential authentication. The system BiometricPrompt receives the exact
Cipher used to unwrap the secret. An ordinary prompt without successful key use
cannot unlock the vault. AAD binds envelopes to app format and UUID slot.

An optional separate password (12-character minimum) wraps the random local secret
using the existing Argon2id MODERATE KDF and XSalsa20-Poly1305 SecretBox before the
Keystore wrapping. Both protections must succeed. Changing/removing it requires
phone authentication plus the current password, followed by authentication of a
new key envelope. Publication is atomic; the old active key is then retired.
Passwords and unlocked key material are not intentionally persisted. Python/Java
runtime strings cannot offer guaranteed memory zeroization; closing the engine
removes its application-level references.

Secure-screen-lock removal or Keystore loss can make local access impossible.
The app never regenerates an existing slot key or replaces the vault on failed
unlock. Keep all local files and restore an exported backup. Adding biometrics is
configured not to invalidate keys because device credential authentication is also
allowed; platform-specific outcomes still require device testing. Phone unlock
alone never runs this app's vault-unwrapping operation.

Vaults, wrapped secrets, temporary encrypted documents and sample data reside in
this package's no-backup private directory. Android cloud backup and device-transfer
backup are disabled. SQLite journals contain ciphertext. A new restore is validated
and staged with a new random local secret before the atomic active-slot marker is
published. A failure keeps the original active vault and marker. Old encrypted slot
files may remain after successful restores; these are not a substitute for an
exported backup and its recovery secret. Uninstall removes private data and keys.

## Portable backup and recovery

Choose **Export portable backup** and set/confirm a password, or generate and record
a recovery key shown in the dialog. Keep the secret separately from the exported
file. The entire signed format-2 SQLite snapshot is copied consistently, then its
Owner credential is rewrapped under the backup secret. The encrypted file is saved
through Android's document picker. It has no dependence on the original phone key.
Use **Restore portable encrypted backup** on a fresh installation, pick that file,
enter the backup secret and choose the replacement phone's optional vault password.
The engine validates policy and every entry before publication. Managed NAS vaults
are rejected; use the companion app for those. Import limit: 64 MiB.

Incorrect secrets and damaged backups must leave the current vault intact. Existing
valid personal backups use Owner internally; no account administration is needed.
Export files remain until you delete them yourself, including after uninstall.
The app does not automatically rotate or prune exported documents. Keep multiple
verified backups and test a fresh-install restoration before trusting them.
Losing the phone **and all usable backup/recovery secrets** means permanent loss.
Deleting an entry is recoverable, not permanent erasure. Copies already exported
retain their contents. Secure physical erasure on flash storage is not guaranteed.

## Desktop and NAS migration

1. In the standalone app choose **Export for desktop and NAS**. Set and confirm a
   new master password (at least 12 characters). Keep it independently of the phone.
2. Save the encrypted `.sqlite` document and transfer it to the desktop. Work from
   a local copy, not directly on the NAS. Keep the standalone app and a backup intact.
3. Open it in the existing desktop Vault with the chosen export password. In a
   personal vault the engine selects its Owner account automatically. Manager can
   open the same local copy; use **Owner** when a username is requested.
4. Establish an SMB shared folder through the desktop's existing sync settings.
   Complete the first desktop sync, creating `wormwright-vault.sqlite` on the share.
   Use a fresh test folder, not an existing personal NAS vault's folder.
5. If separate companion credentials are desired, use desktop Manager to provision
   an account and grant the required Generic group access, then sync the policy.
   After account provisioning, use **Owner** explicitly for desktop administration.
6. In the existing Android companion import a copy of that same migrated vault.
   Authenticate with Owner/export master password or the newly provisioned account.
   Configure its SMB NAS connection and complete initial NAS pairing before editing.
7. Test an invented companion edit and sync, then desktop download; test a desktop
   edit and companion download. Verify all five fields and recoverable deletions.

This export is a real desktop/companion **format-2** vault, not an assumed compatible
opaque Android wrapper. The engine-generated personal Owner account, signing keys,
policy, entry identities, group envelopes, and deleted-entry tombstones are retained.
No entry field conversion is needed. This format does not retain per-entry edit
history, so no historic edit versions can transfer. Migration does not modify the
standalone credential, files, phone-authentication behavior or NAS settings (none).
A portable backup uses the same format but a different purpose/secret. Clearly
label copies so the backup secret and migration master password are not confused.

## Build and signing

Use Gradle 8.13, JDK 17+, SDK platform 36 and build tools 36.0.0. The module uses AGP
8.9.2 and Chaquopy 17.0.0/Python 3.13. Set WORMWRIGHT_BUILD_PYTHON to a compatible
build Python and GRADLE_USER_HOME if using the shared cached dependencies.

`prepare_test_signing.py /private/signing/folder` creates a persistent dedicated
Pocket test key and properties file outside the repository; preserve and privately
back up both. Set WORMWRIGHT_TEST_SIGNING to that properties file for installable
updates signed with this identity. This does not read or reuse companion keys.
Run `gradle assembleDebug lintDebug bundleRelease` from this module.
Without test configuration, developer builds use the host's default debug key.

Production release builds remain **unsigned** unless WORMWRIGHT_RELEASE_SIGNING
points to publisher-controlled properties with storeFile, storePassword, keyAlias,
and keyPassword. Use a separate production upload key and Play App Signing; do not
publish the dedicated test signing identity as the production identity. Changing
from test signing to production signing requires backup, uninstall and restore
unless a deliberate compatible signing arrangement is established. Keep the
permanent package ID and raise versionCode for every distributed update.

`python3 verify_package.py app/build/outputs/apk/debug/app-debug.apk /path/to/sdk`
checks package/API/permissions, signature, 16 KiB APK alignment, and ELF PT_LOAD
alignment of native libraries, including nested Python assets. These checks do not
replace runtime testing on a 16 KiB device or emulator. Dependencies: Chaquopy
runtime, PyNaCl 1.5.0, cffi 1.17.1, chaquopy-libffi 3.3 and pycparser. See licensing
files and vendor notices; preserve distribution/source obligations under GPLv3.

## Release gate

The APK is a test build. Publish the prepared draft GitHub release only after the
user confirms device tests passed. Do not submit it to Google Play. See
DEVICE-TESTS.md and HANDOFF.md for remaining validation and submission requirements.
