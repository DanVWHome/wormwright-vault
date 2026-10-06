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
