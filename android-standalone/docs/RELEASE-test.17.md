# Android .17 — clear YubiKey touch and enrollment status

The enrolled key already works: no re-enrollment or reset is needed.

Both apps show a prominent “Touch your YubiKey now” prompt when the key requests a touch. After the PIN, Continue is removed because the next action is on the physical key. Registration explains when a second touch is needed.

Pocket displays “Vault unlocked with YubiKey.” Manage YubiKeys opens a visible key list immediately, including an explicit empty state, without another phone-PIN prompt. Adding, renaming and removing keys still require fresh phone authorization. Successful enrollment shows a saved-and-verified confirmation with a link to view keys.

YubiKey OTP keyboard input is ignored in vault activity and protected dialog windows, preventing its keystrokes from activating focused buttons such as Help. This is separate from FIDO authentication and makes no changes to the key’s OTP settings. Normal keyboards remain usable.

Install over the existing apps; do not uninstall or clear storage. Existing vaults and key enrollments remain. Desktop Mint stays at 0.3.10. Physical-device confirmation of the new prompts and keyboard filtering is pending.
