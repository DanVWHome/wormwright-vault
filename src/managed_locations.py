"""Device-local managed vault locations; contains paths only."""
import json
import os
import sys
from pathlib import Path
from sync import atomic_json
from platform_paths import data_home


def default_folder():
    return data_home()/'wormwright-vault-beta'


def settings_path():
    return default_folder()/'locations.json'


def read():
    try:
        value=json.loads(settings_path().read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}


def local_folder():
    value=read().get('folder')
    return Path(value) if isinstance(value,str) and Path(value).is_absolute() else default_folder()


def startup_vault():
    value=read().get('last_vault')
    return Path(value) if isinstance(value,str) and Path(value).is_absolute() else local_folder()/'vault.sqlite'


def remember(folder=None,vault=None):
    value=read()
    if folder is not None:value['folder']=str(Path(folder).resolve())
    if vault is not None:value['last_vault']=str(Path(vault).resolve())
    settings_path().parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    atomic_json(settings_path(),value)


def initial_vault(explicit=None, beta=False):
    if explicit is not None:
        return explicit
    if beta or sys.platform == 'win32':
        return startup_vault()
    from hooks import default_vault
    return default_vault()
