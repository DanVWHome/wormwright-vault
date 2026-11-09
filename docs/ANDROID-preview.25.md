# Android companion preview.25

The sign-in screen explains when an account name is required for both password
and YubiKey login. Managed vaults show the notice above the account field;
personal vaults say that the account name can stay blank. Both unlock buttons
stop and focus the account field when a required name is missing, before trying
credentials or reading YubiKey enrollment. Unknown formats retain recovery paths
and show conditional guidance. No usernames or passwords are saved.

Install over the existing companion. Vaults, settings and signing identity are
retained. Mint 0.3.14 remains compatible and needs no update for this change.
