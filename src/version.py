"""Application version and release description shared by the interface."""
VERSION = '0.3.11'
import sys
import platform
RELEASE_LABEL = 'Windows preview 1' if sys.platform == 'win32' else (
    'Fedora preview 1' if platform.freedesktop_os_release().get('ID') == 'fedora'
    else 'Linux Mint release'
)
