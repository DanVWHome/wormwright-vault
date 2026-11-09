FICTIONAL FAMILY — OWNERSHIP AND SHARED PERMISSIONS TEST

All accounts, passwords, codes, financial details and websites in this pack are
invented. Websites use the reserved .invalid domain and will not open a real
service. Do not reuse these demonstration passwords for real accounts.

BUILT-IN DEMO
Mint 0.3.14 and Android companion preview.24 include this second demo.
Imported copies require Mint 0.3.13 / companion preview.23 or newer.

OPEN THE VAULT
On Mint, choose Vault > Load Family Demo Vault (also on the welcome screen).
Save a new local copy, then sign in with one of the fictional logins below.
The original larger demo remains available through Load Demo Vault.
On Android, choose Try the family permissions demo and select a family account.
More > Switch family demo user changes accounts without resetting your edits.
More > Reset family demo restores only this practice copy.
The family demo is separate from real phone vaults and never syncs to your NAS.
You may also transfer a desktop copy to Android and import it as a separate
normal vault if you want to test NAS syncing.

FICTIONAL VAULT ACCOUNT LOGINS (case as shown)
FamilyManager   Demo-Manager-2026!
Dan             Demo-Dan-2026!
Nikki           Demo-Nikki-2026!
Macie           Demo-Macie-2026!
Onyx            Demo-Onyx-2026!

WHERE IS THE MANAGE MENU?
Manage appears only after unlocking with the vault's Manager account. Opening
the Vault Manager application alone does not grant administrative rights.
For this demo, sign in as FamilyManager. Dan and Nikki are ordinary members
of Parents; that group does not make them Managers. Lock, then sign in as
FamilyManager to manage users, groups, exclusions or entry ownership.
Android never provides permission or ownership administration.

GROUPS
Parents: Dan and Nikki, plus the Manager's automatic administrative access.
Family: Dan, Nikki, Macie and Onyx, plus the Manager's automatic access.

EXPECTED ACCESS
FamilyManager: 23 entries. Can view/edit everything, manage permissions and
               transfer ownership.
Dan:           16 entries. Shared Parents and Family entries plus his two gift
               entries. Cannot see Nikki's gifts or Macie's private accounts.
Nikki:         16 entries. Shared Parents and Family entries plus her two gift
               entries. Cannot see Dan's gifts or Macie's private accounts.
Macie:         11 entries. Six Family entries are view-only. Her five private,
               owned entries are editable. Parents entries and gifts are hidden.
Onyx:           1 entry. Netflix only, view-only. Amazon is explicitly excluded,
               along with the door code and every other Family entry.
If you add another shared Family entry, review Onyx’s exclusion for that new
entry. His Netflix-only access uses individual exclusions for current entries.

PARENTS SHARED ENTRIES (8)
Family checking; family savings; electricity; water; home internet; home safe
combination; home/auto insurance; mobile phone plan.

FAMILY SHARED ENTRIES (6)
Amazon Prime; Netflix; front door keypad; guest Wi-Fi; Disney+; family calendar.

PRIVATE GIFT ENTRIES (4)
Dan: gift ideas for Nikki; holiday surprise plans.
Nikki: gift ideas for Dan; anniversary surprise plans.
These entries use Parents with an exclusion for the other parent. Children have
no Parents membership. The Manager can still view every gift entry.

MACIE'S PRIVATE, OWNED ENTRIES (5)
Google email; school portal; public library; art club; game account.
Macie created and owns them. They have no shared group selected, so only Macie
and FamilyManager can see them. Macie can edit them despite shared view-only
status. Other family members cannot see them.

TEST STEPS
1. Log in as FamilyManager and inspect Users & Groups and Individual Exclusions.
2. Lock, log in as Macie, and confirm Amazon/Netflix are visible but Edit/Delete
   are disabled. Select her Google email entry: Edit/Delete should be enabled.
3. As Macie, create a new entry with all group boxes unchecked. She becomes its
   owner automatically. It stays private to Macie and FamilyManager.
4. Lock and log in as Onyx. Only Netflix should appear; editing is blocked.
   Searching for Amazon, the front door code or Macie's email should find none.
5. Compare Dan and Nikki: each sees their own gift ideas but not the other's.
6. To test a transfer, log in as FamilyManager, select Macie's Google email,
   then choose Manage > Change Selected Entry Owner and select Nikki. Macie
   loses access because it is private; Nikki gains access and editing rights.
   The Manager can transfer it back to Macie afterward.

ANDROID EDITING AND SYNC
The built-in Android family demo allows offline practice editing, subject to
entry ownership. It is a local sample and does not connect to NAS.
An imported copy used as a normal companion vault can remain read-only until
its first NAS pairing.
To test editing and sync, use a NEW, EMPTY, DEDICATED NAS subfolder for this test
vault. Configure Mint and Android to use that same test folder and finish the
first sync before testing edits. Do not select your daily-use vault's folder.
Use your own NAS connection credentials; this pack contains no network settings.
A local import's read-only state is separate from account/entry permissions.
Only the desktop manages users, exclusions and ownership transfers. Android
follows the signed policy after syncing. Offline copies keep the old policy
until synced. Owners may create/edit their own private entries; shared view-only
status prevents editing entries owned by someone else.

START OVER
On Mint, load the family demo again and choose a fresh filename. Existing
files are never overwritten. On Android, use More > Reset family demo; that
resets only the sample copy, not your real vaults. For imported-copy NAS tests,
use an untouched file and a fresh dedicated test folder. No YubiKeys are enrolled in
this demonstration vault. The Manager always retains administrative access.
