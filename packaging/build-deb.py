"""Build a bundled .deb from an explicit source allowlist. No vault data included."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'build')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--glibc-min', default='2.39')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    output = args.output_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(work / 'pyinstaller-cache')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--name', 'vanwormai-vault', '--onedir', '--noupx',
                    '--add-data', str(ROOT / 'assets') + ':assets', '--collect-submodules', 'fido2', '--collect-data', 'fido2', '--distpath', str(work / 'bundle'),
                    '--workpath', str(work / 'freeze'), '--specpath', str(work),
                    str(ROOT / 'src/app.py')], check=True)
    subprocess.run([str(work / 'bundle/vanwormai-vault/vanwormai-vault'),
                    '--check-yubikey-runtime'], check=True)
    stage = work / 'deb-root'
    if stage.exists():
        shutil.rmtree(stage)
    library = stage / 'usr/lib/vanwormai-vault'
    shutil.copytree(work / 'bundle/vanwormai-vault', library)
    share = stage / 'usr/share/vanwormai-vault'
    share.mkdir(parents=True)
    for name in ['hooks.py', 'desktop_agent.py']:
        shutil.copy2(ROOT / 'src' / name, share / name)
    for name in ['start.sh', 'vanwormai-vault', 'vanwormai-control', 'vanwormai-enable-desktop-launcher']:
        destination = (share if name == 'start.sh' else stage / 'usr/bin') / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if name in ['start.sh', 'vanwormai-vault']:
            text = '#!/bin/sh\nexec /usr/lib/vanwormai-vault/vanwormai-vault "$@"\n'
        elif name == 'vanwormai-control':
            text = '#!/bin/sh\nexec /usr/bin/python3 /usr/share/vanwormai-vault/hooks.py "$@"\n'
        else:
            text = '''#!/bin/sh
set -eu
folder="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$folder"
cp /usr/share/vanwormai-vault/vanwormai-vault-agent.desktop "$folder/vanwormai-vault-agent.desktop"
nohup /usr/bin/python3 /usr/share/vanwormai-vault/desktop_agent.py </dev/null >/dev/null 2>&1 &
printf '%s\\n' 'Desktop launcher enabled for this login and future logins.'
'''
        destination.write_text(text)
        destination.chmod(0o755)
    for alias, original in [('wormwright-vault', 'vanwormai-vault'), ('wormwright-control', 'vanwormai-control'), ('wormwright-enable-desktop-launcher', 'vanwormai-enable-desktop-launcher')]:
        target = stage / 'usr/bin' / alias
        target.write_text('#!/bin/sh\nexec /usr/bin/' + original + ' "$@"\n')
        target.chmod(0o755)
    shutil.copy2(ROOT / 'packaging/vanwormai-vault-agent.desktop', share / 'vanwormai-vault-agent.desktop')
    applications = stage / 'usr/share/applications'
    applications.mkdir(parents=True)
    shutil.copy2(ROOT / 'packaging/vanwormai-vault.desktop', applications)
    icons = stage / 'usr/share/pixmaps'
    icons.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/wormwright-vault.png', icons / 'vanwormai-vault.png')
    docs = stage / 'usr/share/doc/vanwormai-vault'
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / 'README.md', docs / 'README.md')
    shutil.copy2(ROOT / 'docs/INTEGRATION.txt', docs / 'INTEGRATION.txt')
    notices = docs / 'third-party'
    for name in ['PySide6-Essentials', 'shiboken6', 'PyNaCl', 'cryptography', 'fido2', 'cffi', 'pycparser', 'pyinstaller']:
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or []:
            if 'license' in str(entry).lower() or 'copying' in str(entry).lower():
                source = Path(distribution.locate_file(entry))
                if source.is_file() and source.suffix not in ['.py', '.pyc']:
                    destination = notices / name / entry.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    if (ROOT / 'docs/third-party').exists():
        shutil.copytree(ROOT / 'docs/third-party', notices, dirs_exist_ok=True)
    metadata = stage / 'DEBIAN' 
    metadata.mkdir()
    size = sum(path.stat().st_size for path in stage.rglob('*') if path.is_file()) // 1024
    (metadata / 'control').write_text(f'''Package: vanwormai-vault
Version: 0.1.2
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Wormwright AI Vault Project
Installed-Size: {size}
Depends: libc6 (>= {args.glibc_min}), python3, libxcb-cursor0, libxkbcommon-x11-0, libgl1, libegl1, libfontconfig1, libdbus-1-3, libu2f-udev
Description: Offline encrypted password vault with optional YubiKey unlock
 Prototype desktop vault with local UI-only assistant hooks.
''')
    result = output / 'wormwright-vault_0.1.2_amd64.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(stage), str(result)], check=True)
    print(result)


if __name__ == '__main__':
    main()
