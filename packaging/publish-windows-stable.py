"""Publish the RPM only after the Windows stable validation job succeeds."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
root=Path(__file__).resolve().parents[1]
directory=root/'release-windows'
files=list(directory.rglob('wormwright-vault_0.3.11_windows_x64_setup.exe'))+list(directory.rglob('wormwright-vault_0.3.11_windows_x64.zip'))
assert len(files)==2,files
revision=os.environ['GITHUB_SHA'];repo=os.environ['GITHUB_REPOSITORY']
source=directory/'wormwright-windows-0.3.11-source.zip'
subprocess.run(['git','archive','--format=zip','--output='+str(source),revision],check=True)
notes=directory/'WINDOWS-0.3.11-STABLE.md';shutil.copy2(root/'docs'/notes.name,notes)
files += [source,notes]
sums=directory/'SHA256SUMS';sums.write_text(''.join(hashlib.file_digest(p.open('rb'),'sha256').hexdigest()+'  '+p.name+'\n' for p in files));files.append(sums)
def gh(*args):return subprocess.check_output(['gh',*args,'--repo',repo],text=True)
tag='v0.3.11-windows'
gh('release','create',tag,'--target',revision,'--draft','--title','Wormwright Vault 0.3.11 for Windows','--notes-file',str(notes))
gh('release','upload',tag,*map(str,files));gh('release','edit',tag,'--draft=false','--latest=false')
data=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+tag],text=True))
assert {a['name']:a['digest'] for a in data['assets']}=={p.name:'sha256:'+hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in files}
print('Published and verified',tag)
