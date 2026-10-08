# Wormwright Vault 0.3.2 Windows preview

Windows 10/11 x64. Extract the entire ZIP into a local folder and run
WormwrightVault.exe. Open Manager.cmd opens the Manager interface. No Python
installation is required. This preview is unsigned.

Device-local settings use %LOCALAPPDATA%. Choose a local working vault, and
select a mapped NAS drive or UNC shared folder in NAS settings. Keep the working
vault separate from the shared copy. Windows uses the same encrypted SQLite
formats and reconciliation rules as desktop 0.3.2; there is no format migration.
Android managed-vault support remains limited to the features of its existing
preview; Windows does not change those capabilities.

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
