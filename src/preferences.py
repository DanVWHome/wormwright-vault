"""Device-local app preferences, without vault data."""
import json
import os
from pathlib import Path
from sync import atomic_json

def preferences_path():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'vanwormai-vault/preferences.json'

def read_timeout():
    try:
        value = json.loads(preferences_path().read_text())['lock_minutes']
        return value if type(value) is int and 0 <= value <= 10080 else 5
    except (OSError, ValueError, KeyError, TypeError):
        return 5

def save_timeout(minutes):
    if type(minutes) is not int or not 0 <= minutes <= 10080:
        raise ValueError('Choose Unlimited or between 1 and 10080 minutes.')
    path = preferences_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_json(path, {'lock_minutes': minutes})
