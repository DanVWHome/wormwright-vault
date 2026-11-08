# YubiKey backups, format 3

Native FIDO2/hmac-secret code is adapted from Vault into `ai.wormwright.notes.hardware`, with a separate RP ID `notes.wormwright.local`. Enrollment verifies a fresh signed assertion and UV/UP before saving a registration. Existing credential IDs are excluded during creation to reject a second slot on the same physical key. No OTP, reset or PIN-change operation is present.

A domain-separated HKDF-SHA256 derives a 32-byte X25519 private key from the 32-byte verified PRF output. Only its X25519 public key, public FIDO credential, salt, label and credential fingerprint are retained in the encrypted local registry. No PRF output, YubiKey PIN, symmetric wrapping key or X25519 private key is persisted.

For each new backup, a random AES-256 data key encrypts the whole snapshot. For each of 1–4 recipients, a fresh ephemeral X25519 key agrees with that recipient's public key; HKDF-SHA256 derives a wrapping key, binding the backup ID, credential, salt, recipient and ephemeral public keys. AES-GCM wraps the data key separately for each recipient. The entire versioned header, including all recipient wrappers and labels, is authenticated as payload AAD. Keys and intermediate buffers are cleared after use where mutable.

Restore reads bounded public metadata from the file, obtains a signed/verified assertion from an included physical key and recomputes its private key transiently. It unwraps that recipient's data key and authenticates the full payload/header before parsing or importing notes. Restoring requires no originating-phone registry or Keystore key. A removed or newly added key cannot alter the membership of existing backup files.

Format 3 is `WWNOTES3\n`, a big-endian 4-byte JSON header length, JSON header, 12-byte payload IV, and payload ciphertext/tag. Header is capped at 32 KiB, recipients at four, and file size at 20 MiB. Duplicate recipients, unsupported formats, malformed fields, wrong responses, invalid public keys and modified/truncated envelopes fail closed. A format-3 file never falls back to plaintext or password decryption.

Password format 2 and public JSON remain readable. Password and YubiKey encryption are separate choices; there is no password bypass for a key-only file. File and NAS export use identical bytes and restore logic.

The host hides secret content on pause. Only the exact USB permission overlay can preserve a pending foreground key operation; an actual stop invalidates its generation and phone authorization, cancels connections and rejects late callbacks. The native adapter retains Vault's no-auto-PIN-retry behavior, keyboard guard, UV/UP/signature checks and foreground NFC lease.

Tests cover RFC 5869 HKDF, four independent simulated key responses restoring one file, wrong keys, recipient/header/payload tampering, fifth/duplicate keys, addition/removal semantics, public-only registration, no-registry restore, password compatibility, canceled/late callbacks and USB permission lifecycle. Real physical Notes USB-C/NFC backup/restore remains to be verified with user hardware.
