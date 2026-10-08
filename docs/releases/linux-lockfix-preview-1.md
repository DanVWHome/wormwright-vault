This Linux Mint candidate addresses sync cleanup paths that can leave `.wormwright-sync-lock` on the NAS. It is a prerelease for testing, not a confirmed resolution of the reported intermittent lock. Stable 0.3.2 remains the current stable release.

Changes:
- Release the owned lock even if sync scratch creation or temporary-file cleanup fails.
- Retry lock removal three times for short-lived NAS failures, then show an explicit cleanup error.
- Preserve the existing lock directory protocol, vault formats, merge behavior and protection against simultaneous syncs. Existing locks are not cleared automatically.

Installation: back up your encrypted vault, fully exit Vault and Manager, then install `wormwright-vault-mint_0.3.2+lockfix.1_amd64.deb`. It upgrades the existing Mint package without moving your vault. The app identifies itself as **0.3.2+lockfix.1 · Linux Mint lock-fix preview**. The supported platform remains Linux Mint 22.x on Intel/AMD 64-bit computers.

Testing: use the candidate over time. For an initial isolated sync test, fully exit apps on the other devices; a locked desktop app can still run automatic sync. If a lock returns, record the exact error, time, devices running and any NAS disconnection or computer sleep. Abrupt process termination or a disconnected NAS can still prevent lock removal.

Validation: GitHub Actions passed the synthetic vault, sync, merge/conflict, baseline, cleanup-failure, signed FIDO2, backup/export, UI and package-layout checks. The packaged YubiKey runtime-data check also passed. Real NAS behavior and physical YubiKey use are not verified by these automated checks.

The attached source ZIP is the corresponding source for this build, including its preview version label. Application code is GPLv3 only; dependency notices remain applicable. SHA256SUMS is included.
