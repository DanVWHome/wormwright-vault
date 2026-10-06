"""Run independent dummy-data regressions. No user's real vault is accessed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

checks = Path(__file__).resolve().parent / 'checks'
with tempfile.TemporaryDirectory(prefix='vanwormai-tests-') as directory:
    environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_DATA_HOME': directory,
                   'XDG_RUNTIME_DIR': directory}
    for check in sorted(checks.glob('test_*.py')):
        print(check.name, flush=True)
        subprocess.run([sys.executable, str(check)], cwd=directory, env=environment, check=True)
print('All dummy-data checks passed.')
