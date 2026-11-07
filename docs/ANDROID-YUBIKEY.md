# Android YubiKey unlock — device-test builds

Network Vault 0.1.0-preview.14 and Pocket 0.1.0-test.14 add native NFC and USB-C
FIDO2/hmac-secret unlock. No Google Play Services, browser, or Yubico Authenticator
is required by this flow. NFC must be enabled; USB access requires Android consent.

## Network Vault

Enroll the key for the intended account on desktop and transfer/sync that
updated vault to the phone using the existing workflow. On the locked screen,
enter the account name (blank for a personal vault), choose **Unlock with YubiKey
(NFC / USB-C)**, enter the key PIN, then connect or hold the key against the NFC
reader. Complete first NAS pairing with the existing workflow before editing.

The existing desktop format supports one key per account. The phone does not
modify network-vault enrollment. Enrolling a new key on desktop replaces that
account's previous key enrollment; this release does not change that limitation.

## Pocket

Unlock normally, then choose **More → Enroll YubiKey**. A confirmation explains
that the key becomes an alternative to phone authentication and any optional
vault password. Fresh phone authentication (and the optional vault password,
if set) precedes enrollment. PIN verification and a verified test assertion
must finish before saving the wrapping envelope. Existing enrollment is refused,
not replaced. One key per vault is supported in this release.

Lock, choose **Unlock with YubiKey (NFC / USB-C)**, enter the key PIN, then plug in
or hold the key at the NFC reader until completion. Phone unlock and portable
backup recovery remain available. The key wrapping envelope is retained in
portable backups; the restore workflow still requires its backup password.

## Protocol and lifecycle

Both apps share the same foreground-only hardware controller and Java assertion
verifier. It uses YubiKit 2.9.0 for discovery, transport, CTAP, PIN protocols,
ECDH, encryption and MAC operations. RawHmacSecretExtension passes the stored
32-byte salt verbatim, matching desktop python-fido2 hmacGetSecret. It deliberately
does not apply WebAuthn PRF salt hashing. The RP remains atlas-portable.local.

A fresh random challenge is verified against the returned client data. Credential
ID, RP hash, user presence, user verification and the ES256 signature are checked
before using an exactly 32-byte hmac-secret response. ES256 is the supported
credential algorithm, matching the desktop enrollment default. PINs, secrets and
CTAP payloads are not logged; SLF4J has a no-op backend. PIN input is masked,
excluded from saved state/autofill, and cleared after use. Managed memory cannot
guarantee complete zeroization of every SDK/Java/Python copy.

Only one device attempt is accepted per explicit request. Wrong PINs are not
automatically retried. Cancelling, backgrounding, inactivity locking, switching
vaults, or a 60-second timeout invalidates callbacks. Late results cannot reopen
a locked or different vault. Enrollment snapshots bind completion to the current
user, credential, salt and wrapped key. Existing signed-vault checks still run.

## Build and checks

Use Java 17, Gradle 8.13, Android SDK platforms/build tools 35 and 36, Python 3.13
for Chaquopy, and the original signing identities via environment variables.
Do not generate replacement signing identities for installed app updates.

Network: `gradle assembleRelease testDebugUnitTest lintRelease` in android/.
Pocket: `gradle assembleDebug testDebugUnitTest lintDebug` in android-standalone/.
Both modules include ../android-shared Java and Python sources; ship that folder
with corresponding source. The pinned YubiKit dependencies resolve via Maven Central.

With PyNaCl installed, set PYTHONPATH=android-shared/python and run unittest
discovery separately in android-shared/tests, android/tests and
android-standalone/tests. Shared JVM tests verify valid signed assertions and
rejection of modified challenges, replay, incorrect ID/RP, missing presence/UV,
invalid signatures and malformed secret lengths.

## Physical acceptance — not yet performed

First export encrypted backups and verify their recovery secrets. Install as an
update; do not uninstall. Keep the old APKs and desktop vault copy available.

Test both apps with invented data before relying on the change:

- Correct enrolled key over USB-C: one PIN entry plus requested touch unlocks.
- Correct enrolled key over NFC: hold through completion; no vault password needed.
- Wrong key, wrong PIN, key removal, disabled NFC and denied USB permission fail
  without changing data or enrollment. Avoid repeated wrong-PIN tests on a real key.
- First USB consent may background/lock the app on some Android versions. If it
  does, grant access then explicitly retry the operation; do not weaken app locking.
- Cancel, background, lock, screen lock, timeout, switch vaults and rapid repeat
  attempts never accept a late result or leave an unlocked session.
- Network sync/import, permissions, revoked accounts and NAS conflicts still work.
- Pocket phone authentication, optional password, export, restore and deletion work.
- Existing desktop enrollment still unlocks on desktop after mobile use.

Hardware availability and runtime testing on Pixel 10/GrapheneOS are still needed.
Successful compilation and simulated cryptographic tests do not establish physical
USB/NFC interoperability or a security audit.
