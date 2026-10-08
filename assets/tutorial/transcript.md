# Wormwright Vault 0.2.13 — tutorial transcript

Narrated video using actual app screens and disposable demo data. Synthetic English narration generated locally with Piper, en_US-lessac-medium. Interface appearance may differ with your desktop theme.

## 1. Choose the right app

One person, one or several devices: use Wormwright Vault. Use the optional Manager view when several people share one vault with different permissions. This tutorial uses the managed test build.

## 2. Start with a local vault

The introduction offers Create New Vault, Open Existing Vault and Load Demo Vault. The demo is optional. Your local vault can live in any writable local folder; a dedicated local folder is optional.

## 3. Unlock the demo

After Load Demo Vault, choose a new local filename. Sign in as DemoManager with DemoVault123! These are disposable credentials. In a single-user vault the username is hidden; managed vaults show it.

## 4. Find an entry

Search matches description, link and notes. Only entries your account is allowed to access appear. Clear the search to return to the full accessible list.

## 5. Show or copy a password

Select an entry. Show opens a large password window for easy reading. Copy transfers the password without showing it. Copy Field offers the other fields. The app clears its clipboard value after 30 seconds and on lock.

## 6. Add, edit and generate

Add creates an entry; Edit changes it; Clone starts a copy. In Add/Edit, Generate fills a new random password. Review the fields and choose Save. The Manager can assign groups; ordinary users create entries in their own groups.

## 7. Where the settings live

Open Settings for NAS Sync Settings, Sync Now, Lock Settings, Set Up YubiKey and Change Account Password. Settings are available from the main window; the companion shares the same session.

## 8. Set up the shared master

Choose a mounted, writable network folder dedicated to this one vault. Each computer keeps its working file locally. With an empty shared folder, Sync Now publishes the master. SMB or compatible mounted FTP can work; VPN/Twingate can provide network access.

## 9. Automatic sync and backups

Enable Automatic sync, including while locked. The default interval is 30 seconds; change it here. Maximum automatic backups defaults to 10 per copy. Manual backups are kept. The app must remain running for background sync.

## 10. Connect the other devices

Copy the same current encrypted vault to each device, open it locally, then select the same shared folder and Sync Now. Mount paths may differ. Do not create separate new vaults and expect matching filenames to pair them.

## 11. Work offline and resolve differences

Travel with your local vault and edit offline. Reconnect to the share and check sync status. Independent entry changes can combine. Competing edits need review: compare a row, choose a version, then Apply. A selected row alone is not a resolution.

## 12. Automatic locking

Lock Settings controls the inactivity timeout in minutes. The default is five. Zero means Unlimited and requires acknowledging a warning. Unlimited leaves the session open until you lock or close. Both app views lock together.

## 13. Password and YubiKey options

Settings → Set Up YubiKey enrolls a compatible FIDO2 key for PIN and touch. Keep a working password fallback. Change Account Password changes your credentials. Linux needs device permissions; never run the vault with sudo to work around a key error.

## 14. Manager: users and groups

Manage → Users & Groups shows users and groups in separate panes with compact counts. View Accessible Entries, View User Groups and View Members open searchable detail lists. The Manager belongs to every group.

## 15. Create a new user

Enter a unique username and password twice. Choose groups, review which entries will be shared, and confirm creation. Set exclusions if needed. Sync the Manager copy before exporting a database for the new person.

## 16. Individual exclusions

Manage → Individual Exclusions: select a user, search description, link or notes, and check entries they must not access. Filtering preserves checked choices for that user. Save applies them, including choices hidden by the filter.

## 17. Restore deleted entries

Deleted rows have a red tint and a [Deleted] label. Show deleted entries includes them; Only deleted entries hides active entries. Search within the filtered list. Select a deleted entry and Delete becomes Restore. Permanent deletion is Manager-only.

## 18. Export, recovery and CSV

Import / Export / Backup → Export Database creates a Manager-authenticated encrypted copy for a new device or a lost local file. The recipient opens it and configures sync. CSV export also requires reauthentication, but CSV files are UNENCRYPTED.

## 19. Emergency Lockdown

Manage → Emergency Lockdown disables all ordinary users and attempts immediate shared sync while preserving the Manager. Confirm and reauthenticate. Check publication status. Other devices lose access only after downloading it; old offline copies cannot be erased.

## 20. Two views, one session

View → Open Manager View or Open Vault View opens the other app window. Both share the same vault, search, edits and locking. Close the extra view to keep the main session. A Manager launcher never grants rights to an ordinary account.

## 21. AI-assisted lookup

A configured assistant can open or focus the app and look up an entry, such as Gmail. Results stay masked. If locked, you authenticate first. The local hooks return acknowledgments, not passwords or entries, and cannot unlock, reveal or copy passwords. Voice recognition is configured separately.

## 22. Help when you need it

Help → Searchable Help contains grouped topics and numbered guides for new users, lost databases and shared sync setup. Help → About Wormwright Vault explains the purpose, protections and limitations. Practice in a separate demo sync folder.
