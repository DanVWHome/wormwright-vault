"""Bundled, entirely fictional family practice data and offline guide."""
from pathlib import Path
import sys

def asset_folder():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / 'assets/demo'

def guide_text():
    try:return (asset_folder() / 'family-demo-readme.txt').read_text()
    except OSError:return 'The family demo guide is unavailable. Reinstall the app to restore its bundled help.'
