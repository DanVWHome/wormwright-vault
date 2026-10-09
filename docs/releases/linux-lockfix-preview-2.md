This Linux Mint prerelease fixes an SMB/GVFS upload failure: `[Errno 95] Operation not supported` on a `.wormwright-managed-…sqlite` temporary upload. The previous shared file remains untouched when this failure occurs; local edits are retained.

The cause was a read/write reopen introduced for Windows compatibility. GVFS SMB can reject that mode even though separate writes, reads and replacement renames work. The corrected path flushes the write handle, closes it, verifies the uploaded bytes using a separate read handle, then replaces the shared file. Verification or I/O failures prevent replacement.

The fix was verified with synthetic temporary files on the affected real SMB mount. Automated tests cover unsupported read/write reopening, unsupported fsync, real I/O failures, corrupt transfers and cleanup, alongside the existing vault/sync compatibility checks. This is not proof that every intermittent NAS-lock issue is resolved.

This build retains preview 1's lock-cleanup improvements. Vault formats, NAS filenames, reconciliation rules and existing YubiKey enrollment remain unchanged. Use SMB; FTP-mounted shares have shown intermittent sync/lock failures.

Back up your encrypted local vault—including unsynced edits—and fully exit Vault and Manager before installing `wormwright-vault-mint_0.3.2+lockfix.2_amd64.deb`. Install over the existing Mint package and reopen the same local vault. Do not replace your local copy with an older NAS copy. The app displays **0.3.2+lockfix.2 · Linux Mint NAS sync preview 2**. Platform: Linux Mint 22.x, Intel/AMD x64.

Application code is GPLv3 only; dependency notices and branding exclusions remain applicable. Corresponding build source and SHA256SUMS are attached. Linux 0.3.2 remains the latest stable release. Existing Windows release files are unchanged.
