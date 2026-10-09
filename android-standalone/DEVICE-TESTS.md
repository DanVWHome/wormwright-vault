# Required device acceptance — invented data only

Record phone/Android version, app version and outcome beside each item. Do not
attach personal vaults, PINs, passwords, recovery keys or NAS credentials to reports.
Dan confirmed test.2 downloaded and installed, then reported camera overlap and
record-layout issues. Remaining checks require explicit results on the phone.

- Check test.4 home, list and search screens in portrait and landscape. Text
  and controls must stay clear of the camera, status/navigation bars and keyboard,
  including while scrolling. Open a sample record: description is the title,
  fields appear together, all actions are grouped, Show/Hide toggles, and each
  copy action copies its intended field. Check long notes and large text size.
- Confirm opening immediately shows a spinner and blocks duplicate attempts. Open
  a record, edit, save, reopen and cancel repeatedly without a crash. Check errors
  and locking clear the indicator. Automated emulator results do not replace
  personal-vault authentication and real phone checks.
- Confirm both launcher entries: existing companion `ai.wormwright.vault.preview`
  and standalone `ai.wormwright.vault.standalone`. Install Pocket while companion
  remains installed. Do not import, read, edit or sync the existing personal vault.
- With a securely locked phone, create personal vault without optional password;
  authenticate using strong biometrics, then explicitly test PIN/pattern/password
  fallback. Cancel each prompt and fail biometric attempts; vault must remain locked.
- Create/edit/view/search/copy all fields, including Unicode and multiline notes;
  delete and restore an entry. Verify sample changes cannot affect personal data.
- Leave the app, switch apps, lock the screen, rotate, wait two idle minutes, kill
  its process and relaunch. Every locked personal-vault reopening must authenticate
  within Vault; unlocking the phone alone must not reveal data.
- Copy a secret: verify clipboard clears after 30 seconds and immediately on lock.
  Copy unrelated text in another app and verify Pocket does not clear that text.
  Test screenshots, recent-app thumbnails and password/recovery dialogs are blocked.
- Enable optional vault password. Phone authentication alone and an incorrect
  password must fail. Change it using the old password; verify the old password
  fails on the active vault. Remove it explicitly; verify phone authentication
  remains necessary. Cancel at each step; existing data must remain accessible.
- Export with backup password and with generated recovery key. Record the secret
  separately and restore both. Wrong secret, truncation and modified ciphertext
  must be rejected without altering the original active vault.
- Restore on a **fresh installation on a second device** or after safe uninstall of
  Pocket only. Do not bring over original device keys. Verify all fields/deletions.
- With an invented vault and verified external backup only, add/remove biometrics,
  change the phone PIN and remove/re-establish screen lock. Confirm no silent key
  regeneration or vault replacement. When unavailable, restore the external backup.
- Disable network/enable airplane mode and repeat creation, CRUD, locking, copying,
  backup and restore to a local document provider. No network is needed by Pocket.
- Install a same-key higher-version Pocket build over it and verify its data.
  Uninstall Pocket only and confirm the existing companion still launches with its
  configuration retained. Use synthetic companion data for mutation/sync tests;
  never replace the companion's existing personal vault to run this test. A second
  test phone/profile with synthetic companion installation is recommended.
- Run the full README migration sequence through the **actual desktop UI, an SMB
  NAS share and companion Android UI**. Verify all fields, account provisioning,
  initial pairing, companion→NAS→desktop and desktop→NAS→companion changes,
  recoverable deleted entries and the standalone vault remaining intact. Automated
  shared-directory engine checks alone do not satisfy this acceptance item.
- Run on arm64 and, where possible, a 16 KiB memory-page device/emulator. Check
  startup, Python crypto loading, authentication and restore performance.

After testing, send the completed checklist and any failures. Release publication
requires explicit confirmation that these device tests passed. No public release or
Play submission should be treated as approved merely because the APK installs.

## Fresh vault and deletion

Create a second invented personal vault, cancel once, complete creation, and switch back to the original. Verify both remain accessible. Cancel deletion at authentication and final review. Confirm wrong or missing DELETE removes nothing. Authorize Delete all phone vaults with/without optional password and verify retained copies are gone and creation becomes available. Export invented backups, select multiple files using Delete selected backups, cancel once, then authorize and confirm. Verify only selected files are removed and report any provider failures; check provider trash separately.

## Named vaults and individual deletion

Reject a blank name. Create differently named vaults; close and reopen the app and verify the named chooser and current marker. Rename an older unnamed vault after inspecting its entries. Cancel at the named deletion chooser, before authentication and at the final review; verify all files remain. Delete a noncurrent vault and a current vault with/without an optional password; verify only the chosen vault and its key are gone, remaining vaults still open, and exported backups remain.
