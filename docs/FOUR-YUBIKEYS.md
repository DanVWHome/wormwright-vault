# Four named keys per vault account

Desktop 0.3.9, Network Vault preview.15, Pocket test.15.

Enroll up to four credentials per vault account, with names such as Laptop,
Phone, Backup and Spare. Adding a key appends an independent wrapping envelope;
it never replaces another enrolled key. Select the intended key by name before
using its PIN. A fifth enrollment is rejected without changing existing keys.

## Update and enroll

Export encrypted backups and preserve recovery secrets first. Update every
computer and phone app that opens/synchronizes this vault BEFORE adding keys.
Old builds do not understand the new collection and must not manage enrollment.
Existing single-key records are read without changing them; adding, renaming or
removing a key writes a version-2 key collection. Existing credentials, salts,
wrapped keys, account passwords and encrypted entries are preserved.

Desktop: unlock normally. Use Add YubiKey, authenticate, give it a unique name,
Unplug all current YubiKeys first, authorize using your account password, then
connect only the new key when prompted and perform its PIN/touch enrollment. Repeat for the other keys.
Manage YubiKeys renames/removes a selected enrollment after fresh authentication.
Only current-account keys are displayed. A legacy key starts as Original key;
rename it Laptop if appropriate. PINs can be different on each physical key.

Network Android: manage enrollment on desktop and synchronize/import the updated
vault using the established workflow. Unlock with YubiKey offers a named key
selector. Then enter that key's PIN and use NFC or USB-C. No PIN is trialled
against other keys. Normal password unlock remains available.

Pocket: unlock normally, then More > Enroll YubiKey. Confirm the alternative
unlock method, confirm your phone credential, and name/enroll each key. More > Manage
YubiKeys renames or removes a key after fresh phone authentication.
The YubiKey path replaces phone authentication and any optional vault password
for that unlock. Existing phone authentication remains available.

## Removal, backup, sync and limits

Removing a key affects this copy and copies which receive the updated vault.
It does not erase the physical credential from the key, revoke access to older
backups/offline copies, or rotate every encrypted entry key. Keep old backups
secure. Removal is not retroactive hardware-key revocation across offline copies.

Backup/export/restore retain every hardware envelope. Changing an account's
password preserves its keys; management disabling still denies all that account's
keys on updated copies. A backup made before a new enrollment lacks that new key.
Pocket's exported backup still requires its recovery password for the restore
workflow. Keep a recovery method independent of the carried phone/key.

Security changes (including key-list changes) retain the existing administrative
sync conflict rules: competing local/NAS key edits require review, rather than
silently merging or dropping one side. Each append/remove/rename is transactional,
and append checks capacity/duplicate names/credentials inside the write lock.
A queued assertion for a removed or renamed enrollment is rejected; adding another
key does not invalidate an unchanged existing key's assertion.

Four means four credential enrollments, not automatic physical-device detection.
A key registered twice can create two different credentials; name keys clearly.
The app does not copy credentials from one physical YubiKey onto another.

This changes enrollment storage and selection only. Existing FIDO2 PIN/touch,
ES256 assertion verification, raw hmac-secret derivation and foreground-only
NFC/USB lifecycle handling remain. No PINs or hardware response secrets are stored.
Full handset NFC/USB behavior still requires testing with real keys on GrapheneOS.
