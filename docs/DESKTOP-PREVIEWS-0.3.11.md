# Windows and Fedora 0.3.11 preview 1

These previews bring the current desktop vault code to Windows x64 and Fedora
44 x86_64. They include up to four named YubiKeys per vault account, automatic
matching of the connected key, password-authorized enrollment of additional
keys, clearer PIN failures, and “Which key are you managing?” wording.

YubiKey unlock continues to require the physical key and its PIN. Existing
vaults and enrollments remain compatible; no key reset or re-enrollment is
needed. Mint stays on its existing 0.3.11 release. No Android keyboard preference
is added to desktop PIN prompts.

Install the Windows setup EXE over the existing installation, or extract the
complete portable ZIP. Fully close Vault and Manager before updating. On Fedora,
use `sudo dnf install ./wormwright-vault-0.3.11-1.fc44.x86_64.rpm`.
Save an encrypted backup first. The installers contain no personal vaults or
pre-enrolled personal keys. Both previews retain the existing platform's package
identity and vault settings locations.

The Windows build pipeline checks synthetic vault/crypto/sync regressions,
four-key behavior and automatic matching, bundled runtime, executable icons,
portable startup, installation, upgrade and uninstall with invented data.
The Fedora pipeline checks the same portable and multiple-key regressions,
bundled runtime and RPM metadata, then installs the RPM and checks offscreen
startup and removal in a Fedora 44 container. These are automated checks;
real security-key prompts, desktop display and NAS sync need user testing on
each target machine. The RPM is unsigned, as in the previous Fedora preview.
Windows binaries are not Authenticode-signed. Verify downloads against the
SHA256SUMS file on the same official release.

## Suggested user test

Open an existing vault, confirm password and YubiKey unlock, test the main and
backup keys without choosing a key name, then verify adding/renaming/removing a
key using an invented vault. Check Vault and Manager, window layout, remembered
settings, tutorial playback and SMB sync in both directions. Do not reset keys
or deliberately exhaust PIN attempts. Report the platform/version and exact
error if anything fails. Keep your working Mint/Android installations available.

## Android testing status

The user confirmed both Pocket 0.1.0-test.21 and Network/NAS 0.1.0-preview.21
passed testing on Google Pixel 10 with GrapheneOS: numeric keypad, switching
between numbers and letters/symbols, and USB-C and NFC authentication. This is
confirmation on that device, not a claim about every Android phone.
