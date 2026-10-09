# Wormwright Vault 0.3.2 Windows preview 2

Windows 10/11 x64. Extract the entire ZIP into a local folder and run
WormwrightVault.exe. Open Manager.cmd opens the Manager interface. No Python
installation is required. This preview is unsigned.

Windows remembers your last selected vault on restart, including its saved NAS settings.
The initial window fits the usable screen area. YubiKey operations use the native
Windows security-key prompt; enter the key PIN there. Use your existing enrolled
key without resetting or registering it again for Windows. Password and existing YubiKey unlock, remembered vault and NAS settings,
and window sizing have been confirmed on one Windows laptop. Other devices
and NAS scenarios remain subject to testing.

Device-local settings use %LOCALAPPDATA%. Choose a local working vault, and
select a mapped SMB NAS drive or UNC shared folder in NAS settings.
FTP-mounted shares have shown intermittent sync/lock failures; use SMB instead. Keep the working
vault separate from the shared copy. Windows uses the same encrypted SQLite
formats and reconciliation rules as desktop 0.3.2; there is no format migration.
Android managed-vault support remains limited to the features of its existing
preview; Windows does not change those capabilities.

## Installer

The Windows preview 2 release also provides
`wormwright-vault_0.3.2_windows_x64_preview2_setup.exe`. Close Vault and Manager,
run setup, then open Wormwright Vault or Wormwright Vault Manager from the
Start menu. The optional desktop shortcut opens Vault. Setup installs per user
in `%LOCALAPPDATA%\Programs\Wormwright Vault`; no administrator access or Python
installation is required. The installer is unsigned. It wraps the exact tested
portable preview 2 binaries, without changing vault formats or sync behavior.

Updating and uninstalling preserve separately stored vault files and settings.
For a previous portable installation, close the old copy and use the new Start
menu shortcuts. The ZIP remains available for portable use.

GitHub Actions verifies install, reinstall, executable identity, startup and
uninstall against synthetic data. Physical Windows installer testing remains
necessary. Installer packaging source is provided as a separate release archive;
application source corresponds to the original preview 2 source archive.

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
