"""Synthetic locations only; never reads the user's recent vaults."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from history import VaultHistory, MAX_RECENT

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    history = VaultHistory(root / 'history.json')
    assert history.read() == []
    for index in range(MAX_RECENT + 5):
        history.remember(root / f'fictional-{index}.sqlite')
    assert len(history.read()) == MAX_RECENT
    newest = history.read()[0]
    history.remember(newest)
    assert history.read()[0] == newest and len(history.read()) == MAX_RECENT
    assert history.path.stat().st_mode & 0o777 == 0o600
    vault = root / 'keep.sqlite'; vault.write_bytes(b'dummy-file')
    history.remember(vault)
    history.forget(str(vault))
    assert vault.read_bytes() == b'dummy-file' and str(vault) not in history.read()
    history.path.write_text('invalid json')
    assert history.read() == []
    history.remember(vault)
    assert VaultHistory(history.path).read() == [str(vault)]
print('PASS: recent history persistence, ordering, deduplication, bounds, permissions and forget without deletion')
