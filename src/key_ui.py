"""Windows asks for the security-key PIN in its own trusted prompt."""
import sys
from PySide6.QtWidgets import QInputDialog, QLineEdit


def request_key_pin(parent, title, label='FIDO2 PIN:'):
    if sys.platform == 'win32':
        return None, True
    return QInputDialog.getText(parent, title, label, QLineEdit.EchoMode.Password)


def choose_key(parent, keys):
    """Select the enrollment to rename or remove, not the key authenticating."""
    from PySide6.QtWidgets import QInputDialog
    if not keys:
        from vault import VaultError
        raise VaultError('No YubiKey is enrolled for this account.')
    if len(keys) == 1:
        return keys[0]
    names = [k['label'] for k in keys]
    name, ok = QInputDialog.getItem(parent, 'Manage YubiKeys', 'Which key are you managing?', names, 0, False)
    return keys[names.index(name)] if ok else None


ENROLLMENT_STEPS = {
    1: ('Step 1 of 2: Create key credential',
        'Windows will create a credential on your YubiKey. Choose Security key, '
        'enter the YubiKey PIN, then touch its gold contact when prompted.\n\n'
        'There are two separate operations. After this step, you will enter the '
        'same key PIN and touch the same key again to finish enrollment.'),
    2: ('Step 2 of 2: Verify key and finish enrollment',
        'The key credential was created. Keep the SAME YubiKey connected.\n\n'
        'Windows will now ask you to sign in with that key. Choose Security key '
        'again if asked, enter its PIN again, then touch it again. This obtains '
        'the secret needed for vault unlock and verifies the new credential. '
        'Enrollment is not complete until this step succeeds. This does not add a second key.')
}


def enroll_with_guidance(parent, pin):
    from yubikey_auth import enroll
    if sys.platform == 'win32':
        return parent.key_request(lambda event, stage: enroll(pin, event, stage), enrollment=True)
    return parent.key_request(lambda event: enroll(pin, event))
