"""Device-local managed vault locations; contains paths only."""
import json
import os
from pathlib import Path
from sync import atomic_json


def default_folder():
    return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'wormwright-vault-beta'


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
