"""Linux Mint release package; upgrades the managed beta without moving vaults."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from version import VERSION

def prepare(stage):
    old='wormwright-vault-managed-beta';new='wormwright-vault-mint'
    (stage/'usr/lib'/old).rename(stage/'usr/lib'/new)
    (stage/'usr/share/doc'/old).rename(stage/'usr/share/doc'/new)
    applications=stage/'usr/share/applications';shutil.rmtree(applications);applications.mkdir()
    icons=stage/'usr/share/pixmaps';shutil.rmtree(icons);icons.mkdir()
    binary=stage/'usr/bin';shutil.rmtree(binary);binary.mkdir()
    for name,flags,title,icon in [('wormwright-vault-mint','--beta','Wormwright Vault','wormwright-vault.png'),('wormwright-vault-manager-mint','--beta --manager','Wormwright Vault Manager','wormwright-vault-manager.png')]:
        wrapper=binary/name;wrapper.write_text('#!/bin/sh\nexec /usr/lib/'+new+'/vanwormai-vault '+flags+' "$@"\n');wrapper.chmod(0o755)
        (applications/(name+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+title+'\nExec='+name+'\nIcon='+name+'\nTerminal=false\nCategories=Utility;Security;\n')
        shutil.copy2(ROOT/'assets'/icon,icons/(name+'.png'))
    # Existing shortcuts keep working after the package replaces the beta.
    for alias,target in [('wormwright-vault-beta','wormwright-vault-mint'),('wormwright-vault-manager-beta','wormwright-vault-manager-mint')]:
        wrapper=binary/alias;wrapper.write_text('#!/bin/sh\nexec /usr/bin/'+target+' "$@"\n');wrapper.chmod(0o755)
    share=stage/'usr/share'/new;share.mkdir()
    shutil.copy2(ROOT/'src/hooks.py',share/'hooks.py')
    launcher=share/'start.sh';launcher.write_text('#!/bin/sh\nexec /usr/bin/wormwright-vault-mint "$@"\n');launcher.chmod(0o755)
    control=binary/'wormwright-control-mint';control.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/share/'+new+'/hooks.py "$@"\n');control.chmod(0o755)
    docs=stage/'usr/share/doc'/new
    for name in ('MINT-RELEASE.md','MULTIUSER-DESIGN.md','VALIDATION.md'):
        shutil.copy2(ROOT/'docs'/name,docs/name)
    metadata=stage/'DEBIAN/control';text=metadata.read_text().replace('Package: '+old,'Package: '+new)
    text=text.replace('Description: Managed multi-user vault test build, installed alongside personal Vault','Conflicts: '+old+'\nReplaces: '+old+'\nDescription: Offline password vault and optional multi-user Manager for Linux Mint 22.x')
    text=text.replace(' Prototype desktop vault with local UI-only assistant hooks.',' Encrypted local vaults, shared-folder sync and local UI-only assistant hooks.')
    metadata.write_text(text)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    work=args.work_dir.resolve();output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'packaging/build-managed-beta.py'),'--work-dir',str(work),'--output-dir',str(work/'intermediate')],check=True)
    stage=work/'deb-root';prepare(stage)
    result=output/f'wormwright-vault-mint_{VERSION}_amd64.deb'
    subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','-z1','--build',str(stage),str(result)],check=True)
    print(result)
if __name__=='__main__':main()
