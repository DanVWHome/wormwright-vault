# Wormwright Vault roadmap

## Current release

Linux Mint 22.x amd64 is the initial supported release. User testing has covered
three computers, offline edits and conflict resolution, with FTP and SMB NAS
mounts. Retain encrypted backups and synthetic regression checks for updates.

## Next priority: Android

First target: Google Pixel 10 running GrapheneOS, without requiring Google Play
services. Start with a separately signed test APK, synthetic current-format vault
interoperability, local unlock/search/copy and compatible sync to the same NAS.
Do not test mobile writes against the real shared master until interoperability,
permission enforcement and interruption recovery are verified.

Use native Android storage/lifecycle protections and direct SMB access. Evaluate
FTP compatibility separately: do not silently replace required locking/atomic
replacement with unsafe overwrite. Android background work has different timing
constraints from the desktop. Preserve the desktop file format, signed policies,
per-user encryption and merge semantics. The first Android build uses the existing vault account password; YubiKey
support is outside its scope. No Google Play services are required.

## Later platforms and distribution

Broader Ubuntu/Fedora support, macOS, Windows and iOS follow Android. These are
planned targets, not claims of current compatibility. Develop the Wormwright
website/domain and link it to the official repository and public releases.
