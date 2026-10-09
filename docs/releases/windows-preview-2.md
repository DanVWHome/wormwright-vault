Windows 0.3.2 preview 2 is now available as a portable x64 download, including Vault and optional Manager. Extract the entire ZIP into a local folder and run `WormwrightVault.exe`; use `Open Manager.cmd` for Manager. No Python installation is required. The preview is unsigned.

Confirmed on one Windows laptop: password and existing YubiKey unlock, remembered NAS settings and previous vaults, and window sizing that fits the screen. Other Windows machines and NAS scenarios have not yet been verified.

Use SMB for NAS sync, through a mapped drive or UNC shared folder. FTP-mounted shares have shown intermittent failures and incorrect lock messages. Keep a separate local working vault. Existing Linux/Android vault formats, NAS lock names and reconciliation rules are preserved; no format migration or YubiKey re-enrollment is required. Android retains its existing preview limits.

This build also includes the desktop NAS-lock cleanup improvements: guaranteed release attempts after scratch/cleanup failures, limited release retries and an explicit error when removal fails. It does not automatically clear existing locks. The intermittent NAS-lock issue still needs longer-term testing with SMB.

Validation: GitHub Actions passed the synthetic vault, merge/conflict, settings, cleanup, signed FIDO2 and UI checks, then built and smoke-tested the frozen Windows app. Laptop testing confirmed the Windows fixes above. Only the packaged README was refreshed for publication; application binaries are unchanged from the successful build.

For an update, back up the encrypted vault, fully exit Vault and Manager, and extract into a fresh local folder. Reopen your existing local vault. Do not run the shared master directly or overwrite your local vault with an older copy.

Application source is GPLv3 only; third-party notices and branding exclusions remain applicable. Corresponding source and SHA256 checksums are attached. Linux 0.3.2 remains the latest stable release; this Windows download is marked as a prerelease.
