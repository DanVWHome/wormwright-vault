#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if ! .venv/bin/python -c 'import PySide6.QtWidgets, nacl, cryptography; from fido2.client import DefaultClientDataCollector' >/dev/null 2>&1; then
    .venv/bin/python -m ensurepip --upgrade
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python src/app.py "$@"
