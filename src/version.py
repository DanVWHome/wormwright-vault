"""Application version and release description shared by the interface."""
VERSION = '0.3.3'
import sys
RELEASE_LABEL = 'Windows preview 1' if sys.platform == 'win32' else 'Linux Mint release'
