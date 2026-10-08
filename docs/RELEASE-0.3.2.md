# Wormwright Vault 0.3.2

Fixes NAS settings losing the managed vault sync baseline when saving the same shared folder. Without that baseline, different local and shared copies can appear entirely conflicted. Existing settings lost by 0.3.1 are not reconstructed automatically. Preserve unsynced local edits before reconciling with the NAS.

Validation: same-folder save retains the managed baseline even when interval/retention settings change; choosing another folder unpairs correctly. Managed merge, deletion, locked sync and Manager reconciliation checks passed.

When the baseline is missing, entries with identical encrypted contents are now retained automatically; differing or one-sided entries still require explicit review. No unsynced edits are automatically discarded.
