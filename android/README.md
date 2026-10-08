# Wormwright Vault Android preview 3

Signed local preview for Pixel 10 / GrapheneOS, Android 11 or newer. Import a format-2 encrypted SQLite vault, unlock with the existing account, and configure SMB NAS credentials on the phone. Complete the first NAS sync before editing. The phone downloads the authenticated NAS copy to establish a common starting point.

New entries, edits and deletions are saved offline first. Sync runs after unlock, after saving, on demand and every minute while the unlocked app is open. Closing or leaving the app locks it; sync resumes after the next unlock. Network permission must be enabled for this app in GrapheneOS.

Both platforms use the same shared directory lock and unchanged desktop cryptographic engine. Independent entry edits merge. Competing edits require choosing the phone or NAS version. Account/group policy conflicts preserve both copies and require Manager review on Linux; use More → Export encrypted phone backup. Pending edits block replacing the phone vault with an import.

Uploads retain an encrypted NAS backup, write to a unique temporary file, flush and verify the content, then atomically rename over the shared vault. The phone baseline advances only after publication is acknowledged. Local replacements retain ten encrypted backups. NAS backups use the desktop naming scheme and retain ten copies for this master filename.

Preview limitations: no closed-app background sync, Android autofill, hardware keys or Manager account administration. Pixel 10 / GrapheneOS acceptance confirmed: encrypted import, NAS downloads, phone-created entries appearing on Linux, and phone deletions appearing in Manager recovery view.

Build with the workspace Gradle and Android SDK. `prepare_build.py` creates private persistent local signing credentials outside the packaged source. Never distribute the signing key. `package_preview.py` creates the APK, source archive, checksum and verification report. Python interoperability tests run with PyNaCl; JVM transport tests simulate cancellation, contention and interrupted uploads.
