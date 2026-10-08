VANWORMAI VAULT — OFFLINE PROTOTYPE
Dan Van Wormer + AI + a password vault.

LINUX MINT 21+ (CINNAMON OR XFCE)
If needed: sudo apt install python3-venv libxcb-cursor0 libxkbcommon-x11-0
Run ./start.sh in this folder. First launch downloads Python dependencies;
subsequent launches work offline. Python 3.10+ is required.

Create a master password of at least 12 characters and confirm it. Three
dummy entries are created. The demo password previously suggested was
Atlas-Demo-2026!; it is public and intended only for dummy data.
Change Fallback Password permits any non-empty length. You may choose your
Linux login/sudo password, but it remains an independent vault password.
Wormwright AI never invokes sudo or authenticates against Linux. Linux password
changes do not automatically change the vault password.

EXISTING VAULTS
The launcher keeps using ~/.local/share/atlas-portable/demo-vault.sqlite
when it exists, so existing entries and YubiKey enrollment stay available.
New installations use ~/.local/share/vanwormai-vault/demo-vault.sqlite.
$XDG_DATA_HOME overrides ~/.local/share. Choose Vault opens another vault.
./start.sh /absolute/path/new-vault.sqlite creates a vault at a custom path.
The legacy FIDO relying-party ID and encryption context are deliberately
retained internally so existing enrolled keys continue working.

SEARCH AND ENTRY CONTROLS
Search applies SQL LIKE '%term%' to description, username, link, and notes. Standard
SQLite LIKE behavior applies: ASCII case-insensitivity, % matches any number
of characters, and _ matches one character. Usernames and passwords are not
searched. Matching metadata is indexed only in memory, not written to disk.
Add, edit, clone, delete, copy, and per-row Show controls are available. Show opens a separate
resizable window with large password text; the main table remains masked.
Closing, searching, refreshing, or locking clears the display. Double-click an entry to edit it.
App copy buttons clear after 30 seconds if the clipboard still contains the copied value;
clipboard history managers may retain copies. Lock Settings controls automatic locking after inactivity, default five minutes.
Choose 1–10080 minutes or Unlimited (0), with a warning and confirmation.
Unlimited requires manual locking. Keyboard, clicks and scrolling reset the timer.

ENCRYPTION
Argon2id with libsodium MODERATE settings (about 256 MiB memory) derives the
password wrapping key. A random data key encrypts all entry fields using
PyNaCl SecretBox authenticated encryption and fresh nonces. SQLite contains
ciphertext, random IDs, metadata, and optional YubiKey wrapping information.
Record counts and file sizes remain visible. Master passwords, PINs, and
YubiKey-derived secrets are not stored. Files have owner-only permissions.
Python cannot guarantee secure erasure of process memory. Whole-record
rollback or deletion by someone modifying the file is not detected.

YUBIKEY PIN + TOUCH
Use a FIDO2 key with hmac-secret, such as your YubiKey 5 Nano (5.8).
Unlock with the vault password and select Set Up YubiKey. Confirm the vault
password, enter the existing FIDO2 PIN, and touch when the key flashes.
Enrollment may require two touches. The app remains open; PIN + touch is the
primary option, and Use Fallback Password reveals the password option.
Enrollment does not reset the key, modify its PIN, enable OTP, or change
existing Linux/site credentials. Only one key is enrolled per vault in this
prototype; enrolling another replaces it after confirmation. A safety backup
is saved before enrollment or password changes. Either the key OR the
fallback password unlocks; this is not a requirement to supply both factors.
A key reset invalidates its previous credential. Use the fallback to enroll
a replacement. Do not run Wormwright AI with sudo. Physical enrollment/unlock
still needs verification on your laptop; software/protocol tests passed.

BACKUP AND RESTORE
Back Up Vault creates a consistent encrypted SQLite snapshot at a new path.
It never overwrites an existing file. Store another copy on a separate drive
or your home server. A backup retains its password and key enrollment from
the time it was created. Old backups still work with their old passwords.
Restore Backup replaces the whole current vault, not a merge. Supply the
backup's password. The app validates it, creates an encrypted safety backup
beside the current vault, replaces it, and stays open. Wrong passwords or damaged
backups leave the current vault unchanged. Use the restored password or its
enrolled key for future unlocks. One running instance is enforced per vault
path. Backup/restore is not multi-device synchronization.

IMPORT VAULT CSV
Import accepts plain-text CSV with description, link, user_name, pw, and notes
headers. Extra columns are ignored. Preview masks passwords initially; reveal
and verify them, then check the verification box before importing. No legacy
encryption options, encryption keys, or initialization vectors are supported.

LOCAL AI/VOICE HOOKS
./control.sh lookup Gmail
./control.sh open
./control.sh lock
./control.sh capabilities
For a custom vault: ./control.sh lookup Gmail --vault /path/vault.sqlite

Lookup brings the app forward, searches, and selects a matching row WITHOUT
revealing the password. Multiple matches remain visible; an exact description
match is selected preferentially, otherwise the first matching entry. If
locked, the lookup is kept only in memory and applied after manual unlock.
If the app is closed, the hook requests its launch at the unlock screen.
No matches, record names, usernames, notes, passwords, keys, or PINs are
returned through the hook. Its output is a generic acknowledgment.
These are hooks for an assistant/voice tool to invoke; the app does not
listen to the microphone or run an AI service itself. Future integrations
use the versioned allowlist described in INTEGRATION.txt.

PROTOTYPE SCOPE
Continue dummy-data testing before putting real credentials into this app.
Synchronization and forgotten-password recovery are not implemented. Delete
is permanent except for copies retained in backups. Your uploaded source
and CSV are not bundled or imported automatically.

EXPORT TO CSV
Export to CSV saves all entries, including passwords, as plain text after an
explicit warning. Choose a new filename; existing files are never overwritten.
The file uses owner-only permissions and can be imported with Import Vault CSV
using its default plain-text format. Export includes entries outside the current
search. Use Back Up Vault for encrypted backups.

Every CSV export requires fresh authentication: the enrolled YubiKey with PIN
and touch, or the current fallback/master password. Being unlocked alone is
not sufficient. Cancelled or failed authentication creates no export file.

AUTOMATIC SYNC
Sync Settings enables startup, closing and background sync, including while locked.
Default interval is 30 seconds; choose 5–86400 seconds. Saved entry changes upload
immediately, and other devices poll for downloads. Locked transfers copy only
encrypted data; unlocking still verifies and reveals entries. A missing NAS retries
without recurring popups. Conflicts require Sync Now review after unlocking.
Closing waits for a final attempt; an unavailable share or conflict keeps local
changes saved. Forced exit/crash cannot guarantee a final sync. No-change polls
do not create retained backups. Different devices keep their own interval settings.

ENTRY-LEVEL MERGING (0.1.13)
A successful sync establishes encrypted-entry fingerprints on this device. Independent entry edits, additions and deletions merge automatically. Competing edits or delete-versus-edit require Sync Now review. Independent choices are preselected. No plaintext history is saved. Upgrade every device; establish one successful sync before testing offline independent edits. Missing history or different authentication settings still require review.

COPY FIELDS (0.1.14)
Select an entry and choose Copy Field: Description, Link, User Name, Password or Notes. The password row has a direct Copy button without showing the secret. Add/Edit windows have Copy beside every field, including Notes, and copy the current unsaved text. Copies clear after 30 seconds and when locked; later unrelated clipboard content is preserved.
