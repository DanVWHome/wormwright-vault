# Wormwright Vault Android preview 5

Preview 5 immediately shows a spinner and “Opening vault…” while checking the local
encrypted vault or sample, blocks repeat opening attempts, and shows the indicator
during NAS sync. Completion, errors and locking clear it safely. Real Android
regression checks cover opening feedback, duplicate taps and stale completion.
Package and preview signing identity are unchanged; install over preview 4.

Preview 4 puts login fields and buttons ahead of the welcome notes, shortens the account-name placeholder, and keeps the login form scrollable above the keyboard. Help → Wormwright Website opens https://wormwright.com/ in your browser from either the locked or unlocked screen. The link contains no vault or account information.

Signed local preview for Pixel 10 / GrapheneOS, Android 11 or newer. Import a format-2 encrypted SQLite vault, unlock with the existing account, and configure SMB NAS credentials on the phone. Complete the first NAS sync before editing. The phone downloads the authenticated NAS copy to establish a common starting point.

New entries, edits and deletions are saved offline first. Sync runs after unlock, after saving, on demand and every minute while the unlocked app is open. Closing or leaving the app locks it; sync resumes after the next unlock. Network permission must be enabled for this app in GrapheneOS.

Both platforms use the same shared directory lock and unchanged desktop cryptographic engine. Independent entry edits merge. Competing edits require choosing the phone or NAS version. Account/group policy conflicts preserve both copies and require Manager review on Linux; use More → Export encrypted phone backup. Pending edits block replacing the phone vault with an import.

Uploads retain an encrypted NAS backup, write to a unique temporary file, flush and verify the content, then atomically rename over the shared vault. The phone baseline advances only after publication is acknowledged. Local replacements retain ten encrypted backups. NAS backups use the desktop naming scheme and retain ten copies for this master filename.

Preview limitations: no closed-app background sync, Android autofill, hardware keys or Manager account administration. Pixel 10 / GrapheneOS acceptance confirmed: encrypted import, NAS downloads, phone-created entries appearing on Linux, and phone deletions appearing in Manager recovery view.

Build with the workspace Gradle and Android SDK. `prepare_build.py` creates private persistent local signing credentials outside the packaged source. Never distribute the signing key. `package_preview.py` creates the APK, source archive, checksum and verification report. Python interoperability tests run with PyNaCl; JVM transport tests simulate cancellation, contention and interrupted uploads.

Preview.6 keeps the search field enabled and focused as results update, retaining
the keyboard. Pending results cannot be tapped, and older queries cannot replace
newer results. Background NAS sync preserves typing and the current query.

Preview.7 adds Show password to new and existing entry editors. Passwords start
hidden, and the visibility toggle preserves text and cursor position.

## Vault removal and backups

Help includes Create new vault, vault deletion, and Delete selected backups. Deletion requires fresh authorization and typing DELETE after reviewing its scope. Exported backups are selected explicitly in the Android Files picker, where multiple selection can select all backups in a folder. Offline copies and provider trash remain; deletion is not a guarantee of forensic storage erasure.
Delete phone vault removes the working phone copy, private sample/temporary files and stored NAS connection and pairing. It requires account credentials again and fresh phone authentication. Create new vault is available once no working phone copy exists; it makes an independent editable personal vault, never merges into a different NAS vault. Shared managed vaults are created on desktop and imported.

## Named vaults · preview.10

New personal phone vaults require a name. Creating another preserves existing phone vaults. Vaults lists signed names and current selection, with a chooser on reopening when multiple copies exist. Each copy keeps separate NAS settings and its own settings encryption key. Rename current vault applies to independent personal phone vaults; rename shared NAS vaults in the desktop Manager and synchronize/import the named copy. Existing unnamed copies remain usable. Delete current vault removes only the selected copy and its settings after fresh account credentials, phone authorization, named review and typed DELETE. Delete selected vault… starts from the named list. Cancel is available in the chooser, credential prompt and final review. Other phone vaults, NAS masters and exports remain. Display names are visible metadata.

## CSV-safe password generation · preview.11

New and existing entry editors offer Generate password, matching the desktop 24-character alphabet without commas, quotation marks or line breaks. Generated values use cryptographically secure randomness, stay hidden unless Show password is selected, and are committed only by Save. Cancel discards unsaved changes.
