# Wormwright Vault 0.3.12 — view-only users

Adds a Manager-controlled View only permission in Users & Groups, including
when creating users. Users retain password viewing and copying while entry
creation, cloning, editing and deletion are blocked on desktop and Android.
Existing group membership and exclusion rules continue to govern visibility.

Android companion preview.22 enforces the synced permission and offers no
permission-management controls. Update all devices before enabling view-only;
older clients reject vaults once this feature has been enabled. Offline copies
retain old permissions until synced. See VIEW-ONLY-USERS.md for compatibility.

Built on 0.3.11, preserving the current multiple-YubiKey and platform fixes.
Build artifacts are test candidates; this build does not publish a release.
