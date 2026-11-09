# Entry ownership and shared view-only access

Every new entry belongs to the account that creates it. The owner may edit or
soft-delete it even when that account has shared entries set to View only.
The Manager can view and edit every entry. In Manage, select Change Selected
Entry Owner… to transfer it to another enabled account. Ownership changes and
key envelopes are signed by the Manager; a former creator cannot reclaim an
entry by changing its payload. Existing group access is retained on transfer.
For a private entry, the former owner loses access after syncing.

Shared entries still follow user group memberships and individual exclusions.
A view-only user cannot edit another person's shared entry. An explicit
exclusion still removes access, including for an owner. Assigning a new owner
removes an older exclusion for that new owner so they can access their entry.

Restricted users' new entries default to private: leave the group boxes
unchecked for access by the owner and Manager only. Selecting groups shares
the entry with those members. Existing entry sharing can still be changed
only by the Manager. Android shows the owner and applies the same entry-level
editing rules; user permissions and ownership transfers are managed on desktop.

Update Mint to 0.3.13 and the Android companion to preview.23 before using
ownership. Earlier clients reject an ownership-enabled vault. Existing 0.3.12
vaults retain their old account-wide view-only behavior until the Manager
chooses Manage → Enable Owned-Entry Editing or saves a user/group policy
change in the updated app. New vaults enable ownership automatically.
Offline copies retain their previous policy until synced. Stale edits made
before an ownership transfer require Manager reconciliation, not silent merge.

Creator identity is retained separately from the authoritative owner override
in the Manager-signed access policy. The original creator does not retain
private-entry access merely because they created it. The Manager always has
recovery access; parent-private test entries are private from other ordinary
family accounts, not from the Manager.
