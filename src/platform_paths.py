"""Platform-specific device-local storage; shared vault files are unchanged."""
import os
from pathlib import Path
import sys


def data_home():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
