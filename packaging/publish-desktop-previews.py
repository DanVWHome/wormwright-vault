"""Publish only artifacts from both successful platform jobs in this workflow."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
revision = os.environ.get('WORMWRIGHT_BUILD_REVISION', os.environ['GITHUB_SHA'])
source = root / 'wormwright-desktop-0.3.11-preview-source.zip'
subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(source), revision], check=True)
repo = os.environ['GITHUB_REPOSITORY']
for platform, pattern in [('windows', ('*.exe', '*.zip')), ('fedora', ('*.rpm',))]:
    directory = root / 'preview-artifacts' / (platform + '-preview-0.3.11')
    files = sorted(p for glob in pattern for p in directory.rglob(glob))
    assert len(files) == (2 if platform == 'windows' else 1), files
    for name in ('DESKTOP-PREVIEWS-0.3.11.md',):
        shutil.copy2(root / 'docs' / name, directory / name)
    shutil.copy2(source, directory / source.name)
    files += [directory / 'DESKTOP-PREVIEWS-0.3.11.md', directory / source.name]
    sums = directory / 'SHA256SUMS'
    sums.write_text(''.join(hashlib.file_digest(p.open('rb'), 'sha256').hexdigest() + '  ' + p.name + '\n' for p in files))
    files.append(sums)
    tag = 'v0.3.11-' + platform + '-preview.1'
    def gh(*args):
        return subprocess.check_output(['gh', *args, '--repo', repo], text=True)
    gh('release', 'create', tag, '--target', revision, '--draft', '--prerelease', '--title', 'Wormwright Vault 0.3.11 ' + platform.title() + ' preview 1', '--notes-file', str(root / 'docs/DESKTOP-PREVIEWS-0.3.11.md'))
    gh('release', 'upload', tag, *map(str, files))
    gh('release', 'edit', tag, '--draft=false', '--latest=false')
    data = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + repo + '/releases/tags/' + tag], text=True))
    expected = {p.name: 'sha256:' + hashlib.file_digest(p.open('rb'), 'sha256').hexdigest() for p in files}
    assert {a['name']: a['digest'] for a in data['assets']} == expected
    print('Published and verified', tag, flush=True)
