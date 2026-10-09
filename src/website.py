"""Public website navigation, independent of the vault and its current session."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

WEBSITE_URL = 'https://wormwright.com/'

def open_website(owner):
    if not QDesktopServices.openUrl(QUrl(WEBSITE_URL)):
        QMessageBox.warning(owner, 'Cannot open website',
                            'Open https://wormwright.com/ in your browser.')

def add_website_action(menu, owner):
    action = menu.addAction('Wormwright Website…')
    action.setToolTip('Open wormwright.com in your web browser')
    action.triggered.connect(lambda: open_website(owner))
    return action
