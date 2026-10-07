# Wormwright Vault / Vault Manager managed test build (0.2.4)

This is a separate test package, not the daily-use 0.1.15 upgrade. It installs
`wormwright-vault-beta` and `wormwright-vault-manager-beta` side by side with
Wormwright Vault. Its default empty test vault is
`~/.local/share/wormwright-vault-beta/vault.sqlite` (or under XDG_DATA_HOME).
Use dummy accounts and passwords for these first tests. No personal database is
automatically converted, replaced or shared.

The new format contains encrypted users, groups, exclusions and entries even
in personal mode. The initial group is Generic. Choose your own Manager username during creation; the account is identified with [Manager]. The Manager belongs to all groups automatically and cannot be unassigned. Use Rename Manager in Users & Groups to change the name later.
Username is hidden in personal mode, then appears when a second account is
created. Each user has separate password and optional YubiKey enrollment.

## Test in this order

1. Install the managed-beta .deb. Open **Wormwright Vault Manager — Test**.
2. On the welcome screen choose Create New Vault. Enter your Manager username and confirm a 12+ character master password. Open Existing Vault selects an existing new-format local copy; Convert Personal Vault preserves an older vault and creates a separate copy.
3. Add one dummy entry in Generic, then open Users & Groups and add Family.
4. Add an entry in Family using the Manager's multi-select group control.
5. Add Alice and Bob, selecting Family. Carefully review the sharing preview.
6. Lock. Username should now be visible. Unlock as Alice. The Generic entry
   must not appear, including in search or CSV export.
7. Edit Family's entry, create another in Family, and delete one. Deleted
   entries should disappear from Alice's view. Ordinary users cannot change
   the groups of an existing entry.
8. Unlock using your chosen Manager username and check **Show deleted entries**. Deleted rows should
   say Deleted. Edit them, restore one, then verify Alice sees it again.
9. Exclude Alice from a Family entry. Bob should still see it; Alice should
   not. Exclusion overrides group membership and creator ownership.
10. As Manager, permanently delete a dummy record using the confirmation and
    password check. It should be removed from the current database. Existing
    backups can still contain it.
11. Enroll each account's YubiKey with that account's password and PIN/touch.
    Real hardware interaction needs testing; synthetic tests verify separate
    envelopes but do not substitute for key/device testing.
12. Back up the encrypted dummy vault and copy it to another machine's LOCAL
    working folder. Do not open SQLite directly on the NAS.
13. Set the same dedicated NAS folder on both machines. First sync unchanged
    copies to establish pairing. Automatic sync defaults to startup/unlock,
    after saved changes, closing and every 30 seconds, including while locked.
14. Change different entries on the two machines; sync both and verify both
    changes survive. Competing edits open a comparison. Deleted records remain
    encrypted tombstones until the Manager explicitly purges them.
15. Change permissions on one machine and an entry on another. The Manager
    must explicitly reconcile the complete access settings and selected entries.
    Unknown groups require an explicit selection; they never silently become
    Generic. Both original copies are backed up.
16. Repeat with SMB and your mounted FTP location. Use the configured automatic
    backup limit (default 10); no-change polls should create no new backups.

## Conversion

**Convert Personal Vault** makes a new local copy from an authenticated legacy
vault. It never modifies the original. The converted copy starts in personal
mode. Existing YubiKey enrollment remains valid on the original; enroll the
key for the new copy before relying on it. Old 0.1.x clients cannot use the new
format. Keep all shared copies on the same new-format release.

## Security boundaries

Entry descriptions, links, usernames, passwords, notes, group assignments,
deleted flags, user directory and exclusion rules are encrypted. Ordinary users
receive per-entry keys only for their effective access. Copies expose random
record IDs, key-envelope recipient IDs, ciphertext lengths and a hashed login
routing value; username guesses can be checked against that routing value.
Users can share information they already know. Offline copies and backups
retain formerly accessible secrets; this architecture cannot erase knowledge,
force immediate revocation while disconnected, or prevent rollback to an older
valid snapshot. Shared-folder write access can disrupt or delete files.

The Manager owns recovery material. Signed access policy and records prevent
unauthorized edits from being accepted as valid updates under the same vault
identity. The shared folder is snapshot exchange, not a trusted online server.
Use a new dedicated shared test folder rather than your daily-use master.

## Local locations

The Vault menu contains Choose Folder for New Vaults and Vault Locations Explained.
Create New Vault asks for its folder and filename before account credentials.
Existing files are never overwritten. Open Existing Vault browses to a vault
wherever it is stored. The app remembers the last successfully opened or created
vault on this device. Choosing a different folder affects future creation only;
it does not move or lock the current vault. The shared NAS sync folder is a
separate setting and holds exchange copies, not the live working database.

## Main screen menus (both launchers)

Search, Add, Edit, Clone, Delete, Lock and Copy Field stay on the main screen.
Vault holds Open, Create, Recent, Convert and local-folder preferences.
Import / Export / Backup holds file transfer and backup commands.
Manage contains Users & Groups, Individual Exclusions, Restore and Permanent
Delete and appears only for the authenticated Manager. Show deleted entries
remains a visible Manager checkbox. Settings contains NAS sync, Sync Now,
locking, YubiKey enrollment and account password changes.

Local vaults can be saved anywhere on the computer; a dedicated local folder
is optional. Only the shared NAS sync folder must be dedicated to one vault.
