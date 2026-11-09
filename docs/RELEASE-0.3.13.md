# Wormwright Vault 0.3.13 — entry ownership

View-only now applies to entries shared with the account. Users may create
private entries and edit entries they own. The creator becomes the initial
owner automatically. The Manager may view/edit any entry and transfer ownership
using Manage → Change Selected Entry Owner…. Restricted users' new entries
are private by default on desktop and Android.

The Android companion preview.23 enforces per-entry ownership. Ownership and
permission administration remain on desktop. Update both apps before enabling
ownership; older clients reject ownership-enabled policy. Existing vaults can
be enabled through Manage → Enable Owned-Entry Editing. See ENTRY-OWNERSHIP.md.

Release order: Mint and Android first; wait for the owner's device-testing
confirmation before preparing Windows and Fedora versions.
