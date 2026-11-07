# Wormwright Vault 0.3.11 — Windows stable release

Promotes the user-tested Windows preview 2 behavior to a stable Windows release.
The application label and installer names no longer say preview. Fresh update
settings default to Stable, and the running version is 0.3.11. Existing update
preferences are preserved.

If upgrading from a preview, choose Help → Update Settings → Stable, save, then
Help → Check for Updates. Stable 0.3.11 sorts newer than 0.3.11-preview.2.
The existing Preview feed remains a record of the last preview; it is not
mislabelled as a stable release. No uninstall or key re-enrollment is needed.
Close Vault and Manager, retain an encrypted backup, then install the setup EXE
over the existing app. The portable ZIP must be extracted in full.

Vault and Manager retain four named YubiKeys, automatic key matching, and the
two-step enrollment explanations. The user confirmed Windows update discovery,
the improved instructions, and successful key registration in preview 2. The
stable build changes release labels and update defaults, without changing vault
formats, key enrollment data or authentication. Automated Windows regression,
enrollment UI, runtime, startup, icon, install, upgrade and uninstall checks run
again for the final stable installers. These checks do not constitute an
independent security audit or verification of every NAS/Windows configuration.

The Windows installer remains unsigned, as in previous builds; stable release
status does not add an Authenticode signature. Matching GPL source and SHA256SUMS
are supplied. Mint, Fedora and Android packages are unchanged by this release.
