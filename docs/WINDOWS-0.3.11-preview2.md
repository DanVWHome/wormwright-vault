# Windows 0.3.11 preview 2 — clear two-step YubiKey enrollment

Vault and Manager now explain both Windows security-key operations before each
native prompt opens. Step 1 creates the key credential. Step 2 uses the same
key to obtain the secret needed for vault unlock and verify the new credential.
The instructions explain why you must choose Security key, enter the same key
PIN and touch it again. Enrollment is complete only after step 2 succeeds;
the second operation does not add a second enrollment.

Each step has OK and Cancel. Cancelling stops before the next key operation;
existing vaults and enrolled keys are retained. Windows continues to handle
PIN entry and touch. No PIN caching, automatic retries or authentication changes
are introduced. Normal YubiKey unlock remains a single authentication operation.

Install the preview2 setup EXE over the existing Windows installation after
closing Vault and Manager and retaining an encrypted backup. Existing keys do
not need re-enrollment. The portable ZIP must be extracted in full. Windows
binaries remain unsigned, as in previous previews. Matching source and SHA256SUMS
are attached to this release. Mint, Fedora and Android installers are unchanged.

Automated checks exercise the real Qt worker/UI handoff for both numbered steps,
acknowledgment before each hardware call, cancellation before creation or before
verification, and correct enrollment operation order. Existing portable,
multiple-key, runtime, icon, startup, install, upgrade and uninstall checks also
run on Windows. Physical Windows prompt timing still needs user confirmation.
