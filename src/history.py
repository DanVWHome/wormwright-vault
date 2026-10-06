"""Per-device recent vault locations; contains no vault contents or credentials."""
import json
import os
from pathlib import Path
import tempfile

MAX_RECENT = 20


class VaultHistory:
    def __init__(self, path=None):
        data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
        self.path = Path(path) if path else data / 'vanwormai-vault/recent-vaults.json'

    def read(self):
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, list):
                return []
            return list(dict.fromkeys(p for p in data if isinstance(p, str) and Path(p).is_absolute()))[:MAX_RECENT]
        except (OSError, ValueError):
            return []

    def write(self, paths):
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix='.recent-vaults-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(paths[:MAX_RECENT], stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def remember(self, path):
        path = str(Path(path).resolve())
        self.write([path] + [p for p in self.read() if p != path])

    def forget(self, path):
        self.write([p for p in self.read() if p != path])
