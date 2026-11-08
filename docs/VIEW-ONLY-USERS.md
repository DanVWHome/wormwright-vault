# View-only users

On desktop, unlock as Manager and open Users & Groups. Select a user, choose
Permissions…, enable View only, and save. New users can also be created with
View only checked. This shared desktop UI applies across operating systems.
The Manager always retains full access.

View-only users can search, reveal and copy entries they can access. They cannot
create, clone, edit or delete entries, including entries they originally created.
Group memberships and individual exclusions still determine which entries they see.
Unchecking View only restores normal editing access.

Sync distributes this Manager-signed policy to other computers and the Android
companion. Android displays the restriction and enforces it in the vault engine;
its UI and bridge expose no permission-management action. Imported read-only
snapshots remain read only independently of user permissions.

Update every desktop and Android installation before enabling this feature.
Once enabled for any user, the vault retains a signed compatibility marker even
if editing access is subsequently restored. Earlier engines reject that vault
rather than ignoring the restriction. Vaults that have never enabled view-only
users remain compatible with earlier engines. No password or credential reset is
required. Back up the vault before upgrading clients.

Offline copies keep their previous policy until updated. Competing account or
permission changes require the existing Manager reconciliation flow; they are
not silently merged. Previously copied passwords cannot be recalled. Old backups
also contain their original permissions.

Source validation: test_view_only.py covers existing user-owned entries,
creation/edit/delete rejection, forged signed updates, Manager-only management,
Android bridge enforcement, persistence and restored editing. Existing managed
vault, managed sync and Android bridge suites also exercise compatibility.
