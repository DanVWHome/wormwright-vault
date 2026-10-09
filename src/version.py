"""Application version and release description shared by the interface."""
VERSION = '0.3.5'
import sys
RELEASE_LABEL = 'Windows preview 1' if sys.platform == 'win32' else 'Linux Mint release'
