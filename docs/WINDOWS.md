# Wormwright Vault 0.3.14 for Windows

Includes shared view-only access, editable owned entries and Manager ownership transfer; resizable columns and full-link tooltips; a second family permissions demo with searchable Help; and Manager-only group renaming. See [current desktop release notes](docs/DESKTOP-0.3.14-STABLE.md) in the portable ZIP. Manage appears only after unlocking with the actual vault Manager account.

Windows 10/11 x64. Extract the entire ZIP into a local folder and run
WormwrightVault.exe. Open Manager.cmd opens the Manager interface. No Python
installation is required. This Windows release is unsigned.

Windows remembers your last selected vault on restart, including its saved NAS settings.
The initial window fits the usable screen area. YubiKey operations use the native
Windows security-key prompt; enter the key PIN there. Use your existing enrolled
key without resetting or registering it again for Windows. Password and existing YubiKey unlock, remembered vault and NAS settings,
and window sizing have been confirmed on one Windows laptop. Other devices
and NAS scenarios remain subject to testing.

Device-local settings use %LOCALAPPDATA%. Choose a local working vault, and
select a mapped SMB NAS drive or UNC shared folder in NAS settings.
FTP-mounted shares have shown intermittent sync/lock failures; use SMB instead. Keep the working
vault separate from the shared copy. Windows uses the current desktop format and reconciliation rules. Update all clients before enabling owned-entry permissions; older clients reject ownership-enabled vaults. Use Android companion preview.25 for current permissions and account-name login guidance.

## Installer

The stable Windows release provides
`wormwright-vault_0.3.14_windows_x64_setup.exe`. Close Vault and Manager,
run setup, then open Wormwright Vault or Wormwright Vault Manager from the
Start menu. The optional desktop shortcut opens Vault. Setup installs per user
in `%LOCALAPPDATA%\Programs\Wormwright Vault`; no administrator access or Python
installation is required. The installer is unsigned. It wraps the exact checked portable 0.3.14 binaries.

Updating and uninstalling preserve separately stored vault files and settings.
For a previous portable installation, close the old copy and use the new Start
menu shortcuts. The ZIP remains available for portable use.

GitHub Actions verifies install, reinstall, executable identity, startup and
uninstall against synthetic data. Physical Windows installer testing remains
necessary. The GitHub release links to the exact public source commit used for both app and installer packaging.

## Test on the Windows computer

Use synthetic vaults and a separate NAS test folder first. Check personal and
managed vault opening, create/edit/search/copy, lock/unlock and recovery,
Manager/user/group operations, exports and backups. Check YubiKey unlock with
the actual device if used. Open the same vault twice and confirm the existing
window receives the request. Close and reopen it.

Round-trip dummy edits through Linux -> NAS -> Windows -> NAS -> Android -> NAS
-> Linux. Confirm independent edits merge, conflicting edits require review,
deletions propagate, and locked sync retains encrypted contents. Save unchanged
NAS settings after editing interval/retention and verify the 0.3.2 baseline is
retained. Disconnect the NAS and verify local work remains safe; reconnect and
reconcile. Test both mapped drive and UNC paths, including spaces/non-ASCII.

The Linux desktop-agent/autostart shell integration is not packaged on Windows.
The Windows app retains same-user local UI routing through Qt named pipes.
A successful CI build is not a substitute for these machine/NAS/device tests.

## Delete a local vault or its backups

Vault → Delete Local Vault removes the working file and disconnects its local sync settings. Import / Export / Backup → Delete Vault Backups lists matching local/NAS backup copies and lets you add other backup files. Select individual backups or all listed backups. Both actions require an unlocked Manager account, fresh password or YubiKey authentication, exact-file review and typing DELETE. NAS master copies and other devices remain. Deletion does not guarantee forensic erasure or removal of external snapshots.

Vault → Delete Shared NAS Vault is a separate Manager-authorized action for the configured shared master. Disconnect sync on every other device first: another client can recreate the NAS master from its local copy. The command requires current NAS Manager access, refuses a busy NAS sync lock, reviews the exact path, and disconnects this computer. Local copies and backups remain.

Vault 0.3.6 requires names when creating vaults. Vault → Vaults lists names and locations; Rename Current Vault names older files using the unlocked Manager account. Delete Current Local Vault reviews that vault and path, with Cancel, fresh authorization and typed DELETE.

## Stable updates and YubiKey enrollment

Choose Help → Update Settings → Stable, then Check for Updates when moving from a preview. Fresh installations default to Stable. Adding a key explains both Windows PIN-and-touch operations: create the credential, then verify the same key and finish enrollment. See [stable release notes](WINDOWS-0.3.11-STABLE.md).
