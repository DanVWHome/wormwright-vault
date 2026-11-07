# Android .21 — YubiKey PIN keyboard toggle

Both Wormwright Pocket 0.1.0-test.21 and Network/NAS 0.1.0-preview.21
now default to a numeric password keypad for YubiKey PIN entry. A visible
“Use letters and symbols” button switches to the full password keyboard;
“Use numbers” switches back. The same prompt is used for unlocking and enrollment.

Switching retains the entered PIN and selection in the same masked editor.
Numeric mode is a keyboard preference, not a digits-only PIN rule. Existing
FIDO2 PINs containing letters and symbols remain supported, including after
switching back to numbers. Autocorrect, suggestions, autofill, field-state saving
and content capture are disabled; the keyboard is asked not to learn this input.

Authentication, key enrollment records, transport handling and the desktop app
are unchanged. Install over the existing apps using the same signing identities.
Do not uninstall, reset the key, or re-enroll working keys for this update.

The preceding .20 connection fixes passed repeated USB-C and NFC tests in both
apps on Pixel 10/GrapheneOS; the user also confirmed the wrong-PIN alert is clear.
For .21, Android widget tests run in both app test tasks and check both keyboard
modes, repeated switching with a mixed PIN, text/selection preservation, masking,
privacy flags and full-character input through Android's InputConnection.
Build, existing regression tests, lint, APK signatures and 16 KiB alignment are
also checked. Actual keyboard rendering on the physical phone still needs a
quick check after installation; automated widget tests do not operate its keyboard.
