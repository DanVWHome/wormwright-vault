"""Windows asks for the security-key PIN in its own trusted prompt."""
import sys
from PySide6.QtWidgets import QInputDialog, QLineEdit


def request_key_pin(parent, title, label='FIDO2 PIN:'):
    if sys.platform == 'win32':
        return None, True
    return QInputDialog.getText(parent, title, label, QLineEdit.EchoMode.Password)


def choose_key(parent, keys):
    """Select a named enrollment before requesting its PIN; never trial PINs."""
    from PySide6.QtWidgets import QInputDialog
    if not keys:
        from vault import VaultError
        raise VaultError('No YubiKey is enrolled for this account.')
    if len(keys) == 1:
        return keys[0]
    names = [k['label'] for k in keys]
    name, ok = QInputDialog.getItem(parent, 'Choose YubiKey', 'Which key are you using?', names, 0, False)
    return keys[names.index(name)] if ok else None
