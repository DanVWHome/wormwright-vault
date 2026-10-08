"""Build a Windows x64 portable preview using an explicit source allowlist."""
import argparse
import hashlib
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from version import VERSION


def main():
    if sys.platform != 'win32':
        raise SystemExit('Run this builder on Windows.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'build-windows')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist-windows')
    args = parser.parse_args()
    work, output = args.work_dir.resolve(), args.output_dir.resolve()
    work.mkdir(parents=True, exist_ok=True); output.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--name', 'WormwrightVault', '--onedir', '--windowed', '--noupx',
                    '--add-data', str(ROOT / 'assets') + ';assets',
                    '--collect-submodules', 'fido2', '--collect-data', 'fido2',
                    '--distpath', str(work / 'bundle'), '--workpath', str(work / 'freeze'),
                    '--specpath', str(work), str(ROOT / 'src/app.py')], check=True)
    bundle = work / 'bundle/WormwrightVault'
    subprocess.run([str(bundle / 'WormwrightVault.exe'), '--check-yubikey-runtime'], check=True)
    docs = bundle / 'docs'; docs.mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'docs/WINDOWS.md', bundle / 'README.md')
    shutil.copy2(ROOT / 'docs/RELEASE-0.3.2.md', docs)
    shutil.copytree(ROOT / 'docs/third-party', docs / 'third-party', dirs_exist_ok=True)
    for name in ['PySide6-Essentials', 'PySide6-Addons', 'shiboken6', 'PyNaCl',
                 'cryptography', 'fido2', 'cffi', 'pycparser', 'pyinstaller']:
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or []:
            if 'license' in str(entry).lower() or 'copying' in str(entry).lower():
                source = Path(distribution.locate_file(entry))
                if source.is_file() and source.suffix not in ('.py', '.pyc'):
                    destination = docs / 'third-party' / name / entry.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    (bundle / 'Open Manager.cmd').write_text('@echo off\r\nstart "" "%~dp0WormwrightVault.exe" --manager\r\n')
    name = f'wormwright-vault_{VERSION}_windows_x64_preview2'
    archive = Path(shutil.make_archive(str(output / name), 'zip', bundle.parent, bundle.name))
    (output / (archive.name + '.sha256')).write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print(archive)


if __name__ == '__main__':
    main()
