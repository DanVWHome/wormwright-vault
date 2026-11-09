# Wormwright Pocket 0.1.0-test.25

Typing in dialog fields and touching or scrolling a dialog now reset the normal two-minute idle timer. Actual inactivity and leaving the app still lock the vault.

NAS backups check this app’s Network permission before starting and offer an app-settings link if it is blocked. More → Test NAS connection checks saved credentials, folder access, write/read-back verification, rename and cleanup using a temporary random test file, without sending vault data or requiring a backup secret. NAS errors now identify the failing step instead of a generic settings message. The connection issue on the home NAS remains under investigation; these diagnostics identify its actual failing stage.

Existing NAS settings, saved passwords, private password fields, visible Cancel controls and vaults are retained. Install over the current app without uninstalling.
