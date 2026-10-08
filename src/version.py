"""Application version and release description shared by the interface."""
VERSION = '0.3.2'
import sys
RELEASE_LABEL = 'Windows preview' if sys.platform == 'win32' else 'Linux Mint release'
