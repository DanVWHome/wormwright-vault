# Windows and Fedora 0.3.14

Brings the owner-tested Mint 0.3.14 desktop changes to Windows x64 and Fedora 44 x86_64:

- Manager-controlled shared view-only access, editable owned entries, automatic ownership for newly created entries, and Manager ownership transfer.
- Adjustable table columns: drag a heading divider or double-click to fit. Widths are saved on this computer; full links appear on hover.
- A second, fictional family permissions demo. Use Vault → Load Family Demo Vault. Searchable Help includes its accounts, access rules and practice steps.
- Manager-only group renaming in Manage → Users & Groups, preserving members, entries, exclusions and default selection.
- Help explains that Manage appears only after unlocking with the actual vault Manager account.

Use Android companion preview.25 for the latest phone sign-in guidance. Permissions remain managed on desktop. Update all clients before enabling owned-entry permissions; older clients reject ownership-enabled vaults.

Windows: close Vault and Manager, run the installer over the existing installation, or use the portable ZIP. Existing settings and vaults are preserved. The installer uses the existing app identity. Additional local Windows confirmation remains with the owner.

Fedora: close Vault and Manager, then install the RPM using the software installer or `sudo dnf install ./wormwright-vault-0.3.14-3.fc44.x86_64.rpm`. The package upgrades the previous stable version. Fedora 44 x86_64 is the tested packaging target.
