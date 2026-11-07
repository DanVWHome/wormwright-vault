# Automatic YubiKey matching

Mint desktop 0.3.11, Network Android 0.1.0-preview.19 and Pocket 0.1.0-test.19
no longer ask which enrolled key you are using when unlocking or authorizing
with a YubiKey. Enter the connected key's PIN and use the key when prompted.
The authenticator client receives all credentials enrolled for that vault account
and uses the matched credential's original raw unlock salt. It does not try your PIN separately against each enrollment or automatically
retry a rejected PIN.

Key names remain in Manage YubiKeys for selecting a key to rename or remove.
That prompt now says “Which key are you managing?” rather than “using.”
Existing enrollments and vault formats are unchanged; no re-enrollment is needed.
Physical key plus its PIN remain the YubiKey unlock factors. Alternative phone
or vault-password unlock methods remain separate.

Install APKs over the existing apps; do not uninstall or clear storage. Back up
encrypted vaults first and fully close desktop Vault and Manager before installing.
Connect only the intended key on Linux as before. Both Android builds retain
the foreground NFC reader protection from .18 to prevent the key's web link
from taking over after unlock.

The installers contain no pre-enrolled personal keys. A fresh vault starts with
no enrolled keys. Updates and vault backups preserve the user's own enrollments;
unnamed saved enrollments can have labels such as Key 1 or Original key.

Automated tests include real signed assertions selecting each of four credentials,
wrong/unknown credential, invalid signatures, missing PIN verification, correct
per-credential raw salt, fresh Pocket empty key list, reader lifecycle, UI, package
and signing checks. Physical USB-C/NFC auto-matching still needs a phone retest.
The Network/NAS app remains untested on the physical phone. Windows and Fedora
installers are unchanged; their source is updated, but new packages were not built.

Android key discovery now starts when the PIN dialog opens, so the key and PIN
can arrive in either order. Authentication starts once both are ready, exactly
once. Wrong-PIN errors explicitly say the PIN was rejected and stop; remaining
attempts are shown when the key reports them. Both apps show acknowledged error
alerts and restore an unacknowledged alert after returning from the background.
Unexpected interruptions are reported instead of silently returning to login.
These changes still need physical USB-C/NFC testing with both input orders.
