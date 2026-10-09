"""Windows asks for the security-key PIN in its own trusted prompt."""
import sys
from PySide6.QtWidgets import QInputDialog, QLineEdit


def request_key_pin(parent, title, label='FIDO2 PIN:'):
    if sys.platform == 'win32':
        return None, True
    return QInputDialog.getText(parent, title, label, QLineEdit.EchoMode.Password)
