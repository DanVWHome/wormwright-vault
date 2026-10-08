# Validation scope

Tests use dummy vaults in temporary directories and software-generated FIDO
credentials. No personal passwords or uploaded export are used.

The package must be tested after installing on Mint, especially application-menu
launch, YubiKey PIN/touch, fallback password, backup/restore and desktop-agent
cold-start lookup. A package launched inside an external sandbox retains that
sandbox's restrictions. The opt-in launcher must be started by the user in their
normal desktop session; the development agent does not activate it to evade
its own device restrictions.

Source regression suite passed on 2026-10-06, including the optional desktop
launcher cold-start test. The bundled executable was checked offscreen with
a temporary dummy vault. Physical YubiKey access is not verified by these tests.

## Linux Mint 0.3.0 release — 2026-10-07

All 39 synthetic regression scripts passed, including encrypted storage and
policy tamper checks, account isolation, hardware-authentication simulation,
backup/restore, lockdown, export, IPC, sync and entry merging, UI filtering,
selection/scroll, password-header privacy and Mint package upgrade staging.
Tutorial assets were checked; desktop multimedia playback is skipped in the
offscreen suite and had previously been confirmed by the user.

The bundled executable passed its YubiKey runtime-data check. Package metadata
and an APT installation simulation confirm that wormwright-vault-mint 0.3.0
replaces the managed beta. No installer was run against the user system during
these checks. The user reported successful use across three computers, including
offline edits, conflict resolution, and FTP/SMB NAS sync. That is reported device
validation, not an independent security audit or coverage of every Mint machine.


## 0.3.1 desktop and Android preview 3 — 2026-10-08

Desktop: username matching, password exclusion, SQL query handling, ordinary-account/Manager UI and companion-view regression checks passed. Linux Mint installer metadata and upgrade simulation passed. User installed 0.3.1 and confirmed a phone-created entry is found by username.

Android: 22 interoperability/merge tests and 10 transport tests passed, Android lint and signed APK verification passed, and all 138 shipped native modules satisfy 16 KB ELF alignment. Pixel 10 / GrapheneOS acceptance confirmed encrypted import, NAS download, entry creation/upload and deletion; the Manager app displays the deleted entry for recovery. Offline reconnection and interactive competing-edit acceptance remain pending.
