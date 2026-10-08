# Wormwright Vault Manager: implementation design

Status: implemented as a separate 0.2.0 managed test build. The installed daily-use 0.1.15 app remains unchanged. No real vault has been read, migrated or shared during development. Synthetic storage, sync, migration and UI checks accompany the new format; independent security review and real-device testing remain necessary.

## User-facing behavior

- Wormwright Vault continues to open personal vaults without a username field.
- Managed vaults show Username before password or optional YubiKey unlock.
- Each user sees and searches only entries they can decrypt. Hidden entries
  must never reach the table, search index, duplicate-password counts, exports,
  comparison dialogs, assistant hooks or clipboard controls.
- The creator is the Manager, with access to all entries and administration.
- Add/Edit shows group assignment choices for the Manager. Ordinary users choose only their own groups when creating entries and cannot reassign existing entries. Choices
  come from this vault's encrypted group directory. New entries default to Generic.
- The optional companion, Wormwright Vault Manager, manages users, groups,
  memberships, entry assignments and individual exclusions.
- Access means the union of assigned groups, minus individual exclusions.
  Manager access is independent of group assignments and cannot be excluded.
- Generic is the initial group, not an account named Generic. New accounts and
  entries default to it. User creation must preview what that membership grants.
- The companion uses the same storage and authorization library as the main app.
  No separate SQL-editing path may bypass validation or access checks.
- Its icon uses the approved Vault mascot with a small management badge,
  preserving the existing pose and complete silhouette.

## Confirmed decisions

1. Separate password and optional YubiKey enrollment for every user, with Manager recovery.
2. Users may create, edit and soft-delete entries they can access through their groups or created themselves; exclusions override access. The Manager may edit all entries.
3. Only the Manager can view/edit deleted entries, restore them or permanently remove them. A Show deleted entries checkbox controls their visibility. Permanent deletion requires confirmation; retained backups can still contain old records.

## Encryption and schema

Do not reuse the current global data key for ordinary users. All current entry
payloads can be decrypted by anyone holding that key, regardless of SQL filters.

The new format contains metadata, users, groups, exclusions and entries tables,
with random opaque record IDs and encrypted payloads. Entry group membership is
inside the authenticated encrypted entry/administration data, not a readable
group column. Multiple memberships require a list or a join table, not one
scalar group ID. User-to-group memberships are likewise encrypted.

Each entry has its own random encryption key. The Manager can decrypt every
entry. Each allowed user receives a separately encrypted envelope for that
entry key. Do not distribute a common group key: a user excluded from one entry
could still decrypt it with that group key. Group assignments decide recipients;
entry envelopes enforce the decision cryptographically.

Each account has its own credential wrapping material and access keys. Password
unlock uses the existing Argon2id and authenticated-encryption primitives;
YubiKey wraps that account's unlock material rather than the global vault key.
Manager-only encrypted administration records hold the full directory and
policy. Ordinary users receive only their own encrypted profile and authorized
entry keys. Group labels must not reveal unrelated groups to ordinary users.

Use established libsodium/PyNaCl encryption and signing primitives. Authorization
manifests and entry records must be signed by the Manager (or an explicitly
authorized editor if that feature is approved). Verify identities, signatures,
vault binding and key-envelope recipients before decrypting or displaying.
A recipient able to decrypt must not thereby acquire permission to change
groups, enroll another user or manufacture a valid management update.

Readable storage may expose format version, ciphertext sizes, random IDs and
credential-routing material needed before authentication. Passwords, entry
metadata, account directory, group names and exclusions remain encrypted.
Document this metadata boundary instead of claiming whole-file invisibility.

## Migration and compatibility

Add the new tables to every new-format vault, even in personal mode. A personal
vault starts with one Manager and Generic, but exposes no multi-user login UI.

Migrate only after successful authentication, first backing up the original.
Build and validate a separate local file, then replace atomically. Preserve
entries and support password and YubiKey access; do not silently invalidate an
enrolled key. Failed or interrupted migration leaves the old vault usable.

Conversion alone grants no additional person access. Showing the effective
entry list and confirming new recipients is part of activating multi-user mode.
Keep personal daily-use data separate from test vaults during development.

Use a new format version. The 0.1.15 app must reject it clearly; do not disguise
managed data as the legacy format or allow legacy sync to overwrite it. All
participating machines must upgrade before a real managed vault is deployed.

## Sync and offline use

The common NAS folder remains an encrypted snapshot exchange, not a live SQLite
database. Each device keeps its local working copy. Sync fingerprints must cover
all security-relevant tables and envelopes, not just metadata and entries.

Management changes update policies, recipients, key envelopes and affected
entries in one transaction. Merge these changes as one coherent signed change;
never merge a policy from one side with envelopes from the other. Initially,
competing administration changes require Manager review. Ordinary-user conflict
screens cannot decrypt or display inaccessible entries.

Maintain opaque vault identity and authenticated account/session identity when
reopening snapshots. Current reopen_unlocked(data_key), background transfer,
backup/restore, conflict comparison and merge paths assume one global key and
all-record access; every one requires adaptation before enabling managed vaults.

Revocation rotates affected entry keys and removes the revoked envelopes in the
current vault. Offline copies or backups already possessed by a user may still
contain formerly accessible data. A network-share/offline design cannot erase
knowledge or reliably invalidate a disconnected copy. Do not promise immediate
revocation across offline devices or protection against rollback to old backups.

Shared-folder write permissions are separate from cryptographic entry access.
A person with write access can delete or disrupt files even if they cannot
decrypt them. Signed records prevent unnoticed permission edits; they do not
make a shared folder a trusted authorization server.

## Implementation sequence and acceptance checks

1. Resolve account and editing decisions; implement the storage/key-envelope
   layer and synthetic fixtures without modifying the working 0.1.15 app.
2. Test allowed groups, multiple groups, exclusions, unrelated-entry decryption
   failure, user isolation, forged metadata/envelopes and malformed records.
3. Implement backed-up migration and personal mode, then test existing entries,
   enrollment compatibility, backup/restore and interrupted migrations.
4. Adapt sync and merge for the full new format; test independent changes,
   competing administration, revocation, offline copies, crashes and old clients.
5. Add the conditional username UI and Manager group selection. Verify every
   read/copy/export/search/display/assistant path enforces effective access.
6. Build the companion with users/groups/exclusions screens and approved mascot
   icon. Provide an effective-access preview before activating sharing.
7. Package a separate test release, then test on all three Mint machines using
   dummy accounts and entries before considering personal-vault conversion.

This changes the security model substantially. Keep the working personal
release available throughout; do not declare the managed version ready merely
because filtered rows look correct in the interface.
