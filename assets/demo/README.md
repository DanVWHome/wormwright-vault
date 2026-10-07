# Wormwright Vault — disposable demo kit

For the managed test apps (0.2.5). This is a separate, encrypted vault containing only invented accounts and passwords. No YubiKey is enrolled.

## Contents

- 14 accounts: one Manager, 12 enabled ordinary users, one disabled account.
- 10 groups; the Manager automatically belongs to every group.
- 224 entries: 204 active and 20 soft-deleted.
- 24 entries were created by ordinary users.
- Five individual exclusions, overlapping group assignments, duplicate passwords and long notes.

## Open it

1. Copy `wormwright-demo.sqlite` into any local folder you prefer.
2. In either managed test app choose Vault → Open Vault and select that file.
3. Sign in as **DemoManager** with **DemoVault123!**.
4. Open Users & Groups to explore the searchable lists.
5. Lock the vault and sign in as an ordinary account to compare access.

## Login reference

All passwords below are disposable and deliberately easy to remember. Counts are for the original, unchanged demo vault.

| Username | Password | Groups | Visible active entries |
|---|---|---|---|
| DemoManager | DemoVault123! | All groups | 204 (224 with deleted entries shown) |
| Alice | AliceDemo123! | Family, Finance, Home | 61 |
| Bob | BobDemo123! | Family, Home, Travel | 62 |
| Casey | CaseyDemo123! | School, Family | 46 |
| Dana | DanaDemo123! | Office, Services | 63 |
| Eli | EliDemo123! | Lab, Services | 61 |
| Fran | FranDemo123! | Finance, Office | 41 |
| Gale | GaleDemo123! | Guests | 19 |
| Harper | HarperDemo123! | Travel, Services | 62 |
| Indigo | IndigoDemo123! | School, Lab | 42 |
| Jules | JulesDemo123! | Generic | 20 |
| Kai | KaiDemo123! | Family, School, Travel, Home | 84 |
| Lee | LeeDemo123! | Office, Lab, Finance, Services | 98 |
| DisabledDemo | DisabledDemoDemo123! | Generic, Guests | Disabled: login refused |

## Access checks

Each entry below must be hidden from the excluded user, although their group otherwise grants access:

- **Alice** cannot see **Family — Demo Account 01**.
- **Fran** cannot see **Finance — Demo Account 02**.
- **Dana** cannot see **Office — Demo Account 03**.
- **Eli** cannot see **Services — Demo Account 05**.
- **Gale** cannot see **Guests — Demo Account 04**.

## Suggested tests

1. As DemoManager, show deleted entries: each group has accounts 19 and 20 marked deleted. Restore one, then soft-delete it again.
2. As Alice, search `finance`; confirm Finance account 01 is visible, while Family account 01 is excluded.
3. As Gale, see only Guests entries, with Guests account 04 excluded. Searching `finance` should return no entries.
4. As an ordinary user, edit or soft-delete one of your visible entries and add a new entry to your group.
5. As Manager, change a user’s group membership or exclusion, then lock and sign in as that user to check the change.
6. Open both app views and test matching selection, editing, search and locking.
7. Search descriptions, links and notes using `sample12`, `example.com`, and group names.
8. Test duplicate-password indicators: accounts numbered 07 and 14 share a dummy password across groups.
9. For sync testing, copy this same file to each device. Use a NEW, dedicated shared folder for this demo, separate from your personal vault’s sync folder. Pair and sync the copies using Sync Settings.
10. Edit different entries on two devices, then sync. Next edit the same entry on both devices and test conflict resolution.

Keep the ZIP as an untouched starting point. Extract a fresh copy to reset the test data. Changing credentials or entries will change the reference counts. Do not import these dummy entries into your personal vault.
