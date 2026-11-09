# Changes

## Release 8 — November 9, 2026

- Renames the Android version and About label to Release 8, with internal version code 9 for an in-place upgrade.
- Ships as Wormwright-Notes-Release-8.apk using the existing signing identity; checklist behavior and data formats are unchanged.

- User verified that longer checklist items wrap correctly and their full text is readable.
- Promotes the same verified build to a regular release; existing artifact and tag names are retained for compatibility.

- Wraps long checklist items onto multiple lines with rows that grow to show all text.
- Gives item text more room while retaining a 48 dp remove-button touch target.
- Keeps visual line wrapping separate from stored checklist items; pasted/typed line breaks inside one item become spaces.
- Preserves checked state, editing, autosave, secret-field protection, imports and backup formats.


## 0.1.0-preview.7 — November 9, 2026

- Adds an Android plain-text/Markdown share target and More → Import text with explicit Paste.
- Reviews title, text, Note/Checklist choice and checklist preview before Save; Cancel saves nothing.
- Creates new non-secret entries only; incoming shares cannot read, edit or delete existing notes.
- Preserves checked items and note/checklist choice through reopening and backups.
- Migrates the database in place while retaining existing notes, secrets, pins, Trash and NAS/key settings.
- Adds import, migration and real Android share-intent checks. No new service, account or API key is needed.


## 0.1.0-preview.4 — November 7, 2026

- Adds Password and YubiKey choices for encrypted file and NAS backups.
- Registers, renames and removes up to four independent backup YubiKeys using Vault-derived native USB-C/NFC transport and existing FIDO2 PINs.
- Wraps each backup for all currently registered keys, so any one can restore it on another phone.
- Stores only authenticated public registrations on the phone; hardware-derived private backup keys are never saved.
- Restores using the file's embedded registrations and optionally remembers them on the replacement phone.
- Preserves public JSON, previous password backups, phone-PIN secret notes, sharing, NAS settings and signing identity.


## 0.1.0-preview.3 — November 7, 2026

- Adds secret notes and checklists, unlocked with the phone's PIN, pattern or password through Android's credential-only prompt.
- Hides secret titles, text and search matches; keeps Trash previews private.
- Allows sharing after unlock and locks again when leaving the editor or app.
- Encrypts secret content in the local database and protects secret editor snapshots.
- Password-protects complete file/NAS backups when any secret notes exist; restores secrets as locked notes on the receiving phone.
- Preserves previous notes, pins, Trash, app identity, NAS credentials and signing key.
- Adds migration, crypto, lifecycle, sharing and backup tests plus a real PIN test on a disposable Android emulator.

## 0.1.0-preview.2 — November 7, 2026

Uses the selected larger checklist-and-pencil icon. User reported this preview working, including sharing and NAS backups.
