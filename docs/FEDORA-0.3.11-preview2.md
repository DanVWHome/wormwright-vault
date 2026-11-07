# Fedora 0.3.11 preview 2 — fix startup with long vault paths

Fixes `OSError: AF_UNIX path too long`, which could close Vault and Manager
before showing a window. Local control sockets now use a short, private local
runtime directory, with a bounded private /tmp fallback. They are no longer
placed beside a vault or on its NAS share. Vault identity is hashed; ownership,
permissions, symlink rejection, same-user peer checks and the instance lock
remain enforced. Vault contents, passwords and YubiKey enrollments are unchanged.

The RPM is `wormwright-vault-0.3.11-2.fc44.x86_64.rpm`. DNF upgrades revision 1
in place. Fully close Vault and Manager, retain an encrypted backup, download
the RPM, then run from Downloads:

    sudo dnf install ./wormwright-vault-0.3.11-2.fc44.x86_64.rpm

No uninstall or key re-enrollment is needed. Windows, Mint and Android installers
are unchanged by this Fedora-only publication.

Regression checks exercise real local control requests with long vault paths,
long/missing/shared runtime directories, bounded fallback, permissions and
symlink rejection. Fedora 44 container checks install the RPM and launch both
Vault and Manager with long paths using offscreen rendering and an Xvfb X11
display. They also verify reinstall and removal. Physical Fedora GNOME/Wayland,
YubiKey and NAS testing still need user confirmation. This unsigned preview
retains the package identity of the previous Fedora release.
