"""Application version and release description shared by the interface."""
VERSION = '0.3.13'
WINDOWS_PREVIEW = None
import sys
import platform
RELEASE_LABEL = (f'Windows preview {WINDOWS_PREVIEW}' if WINDOWS_PREVIEW else 'Windows release') if sys.platform == 'win32' else (
    'Fedora release' if platform.freedesktop_os_release().get('ID') == 'fedora'
    else 'Linux Mint release'
)
