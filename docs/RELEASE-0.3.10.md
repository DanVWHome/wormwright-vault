# 0.3.10 — clearer new-key enrollment

Add YubiKey now tells you to unplug all current keys, authorize with the vault
account password, and then connect only the new key when prompted. Manager no
longer requests an existing key and immediately tries enrolling that same key.
Existing enrolled keys and four-key support remain intact.

Android companion preview.16 and Pocket test.16 explicitly handle the USB
permission overlay without discarding the pending operation. Contents are hidden
while that dialog is open; leaving the app cancels the operation. Pocket authorizes
key management with fresh phone authentication from an already unlocked vault,
without asking for the optional vault password again. Enrollment success is
reported only after reopening and testing the saved key envelope.

Automated checks do not replace testing with the physical phone and YubiKey.
Retest USB-C enrollment and unlock before relying on hardware unlock.
