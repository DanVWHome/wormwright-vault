# Wormwright Vault 0.3.11 — Fedora stable release

Promotes the user-tested Fedora preview 2 behavior to stable. The application
now says Fedora release; the RPM revision advances to 3 so DNF upgrades the
existing package. Vault formats, authentication, key enrollments and stored
connection settings remain compatible. The short private control-socket fix
for long vault paths is retained. Windows, Mint and Android packages are unchanged.

The user confirmed both enrolled YubiKeys work in Fedora 44 running in system
GNOME Boxes on Linux Mint. After mounting the NAS, both enrollments appeared
in the vault's key-management list. USB redirection must expose the desired
key to the guest. These results do not establish testing on every physical
Fedora machine, desktop environment, or NAS configuration.

Close Vault and Manager, retain an encrypted backup, then download the stable
RPM and install it from the download directory:

    sudo dnf install ./wormwright-vault-0.3.11-3.fc44.x86_64.rpm

No uninstall or key re-enrollment is needed. Mount the NAS before syncing.
Fedora updates remain manual RPM downloads from the website; no Fedora DNF
repository or in-app Fedora update feed is added. The Mint APT repository and
Windows update feed remain specific to those platforms.

The build runs portable regressions, multiple-key and UI checks, RPM metadata
checks, and Fedora 44 container checks for upgrading revision 2 to revision 3,
retaining an invented user-data marker, both Vault and Manager startup with
long paths using offscreen and X11 rendering, reinstall and removal. Stable
status does not imply an independent security audit. This third-party RPM is
unsigned and is not an official Fedora repository package. Matching GPL source
and SHA256SUMS accompany the release.
