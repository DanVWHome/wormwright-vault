"""Build a side-by-side test package; no files owned by the daily-use package."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from version import VERSION

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    work=args.work_dir.resolve();output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'packaging/build-deb.py'),'--work-dir',str(work),'--output-dir',str(work/'intermediate'),'--stage-only'],check=True)
    stage=work/'deb-root'
    (stage/'usr/lib/vanwormai-vault').rename(stage/'usr/lib/wormwright-vault-managed-beta')
    shutil.rmtree(stage/'usr/bin');(stage/'usr/bin').mkdir()
    for name,flags in [('wormwright-vault-beta','--beta'),('wormwright-vault-manager-beta','--beta --manager')]:
        target=stage/'usr/bin'/name;target.write_text('#!/bin/sh\nexec /usr/lib/wormwright-vault-managed-beta/vanwormai-vault '+flags+' "$@"\n');target.chmod(0o755)
    shutil.rmtree(stage/'usr/share/vanwormai-vault')
    applications=stage/'usr/share/applications';shutil.rmtree(applications);applications.mkdir()
    for name,title,icon in [('wormwright-vault-beta','Wormwright Vault — Managed Test','wormwright-vault-beta'),('wormwright-vault-manager-beta','Wormwright Vault Manager — Test','wormwright-vault-manager-beta')]:
        (applications/(name+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+title+'\nExec='+name+'\nIcon='+icon+'\nTerminal=false\nCategories=Utility;Security;\n')
    icons=stage/'usr/share/pixmaps';shutil.rmtree(icons);icons.mkdir()
    shutil.copy2(ROOT/'assets/wormwright-vault.png',icons/'wormwright-vault-beta.png')
    shutil.copy2(ROOT/'assets/wormwright-vault-manager.png',icons/'wormwright-vault-manager-beta.png')
    (stage/'usr/share/doc/vanwormai-vault').rename(stage/'usr/share/doc/wormwright-vault-managed-beta')
    shutil.copy2(ROOT/'docs/MANAGED-TESTING.md',stage/'usr/share/doc/wormwright-vault-managed-beta/MANAGED-TESTING.md')
    control=stage/'DEBIAN/control';control.write_text(control.read_text().replace('Package: vanwormai-vault','Package: wormwright-vault-managed-beta').replace('Offline encrypted password vault with optional YubiKey unlock','Managed multi-user vault test build, installed alongside personal Vault'))
    result=output/f'wormwright-vault-managed-beta_{VERSION}_amd64.deb'
    subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','-z1','--build',str(stage),str(result)],check=True)
    print(result)

if __name__=='__main__':main()
