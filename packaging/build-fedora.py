"""Build a Fedora x86_64 RPM with private bundled Python/Qt libraries."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from version import VERSION


def prepare(source, stage):
    library = stage / 'usr/lib64/wormwright-vault'
    shutil.copytree(source / 'usr/lib/vanwormai-vault', library)
    for name, flags, title, icon in [
        ('wormwright-vault', '--beta', 'Wormwright Vault', 'wormwright-vault.png'),
        ('wormwright-vault-manager', '--beta --manager', 'Wormwright Vault Manager', 'wormwright-vault-manager.png'),
    ]:
        wrapper = stage / 'usr/bin' / name
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text('#!/bin/sh\nexec /usr/lib64/wormwright-vault/vanwormai-vault ' + flags + ' "$@"\n')
        wrapper.chmod(0o755)
        entry = stage / 'usr/share/applications' / (name + '.desktop')
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text('[Desktop Entry]\nType=Application\nName=' + title + '\nExec=' + name + '\nIcon=' + name + '\nTerminal=false\nCategories=Utility;Security;\n')
        dest = stage / 'usr/share/pixmaps' / (name + '.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'assets' / icon, dest)
    share = stage / 'usr/share/wormwright-vault'
    share.mkdir(parents=True)
    shutil.copy2(ROOT / 'src/hooks.py', share / 'hooks.py')
    (share / 'start.sh').write_text('#!/bin/sh\nexec /usr/bin/wormwright-vault "$@"\n')
    (share / 'start.sh').chmod(0o755)
    control = stage / 'usr/bin/wormwright-control'
    control.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/share/wormwright-vault/hooks.py "$@"\n')
    control.chmod(0o755)
    docs = stage / 'usr/share/doc/wormwright-vault'
    shutil.copytree(source / 'usr/share/doc/vanwormai-vault', docs)
    shutil.copy2(ROOT / 'docs/FEDORA.md', docs / 'FEDORA.md')
    shutil.copy2(ROOT / 'docs/RELEASE-0.3.8.md', docs / 'RELEASE-0.3.8.md')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--prepared-stage', type=Path)
    parser.add_argument('--rpmbuild', default='rpmbuild')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    output = args.output_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    source = args.prepared_stage
    if source is None:
        subprocess.run([sys.executable, str(ROOT / 'packaging/build-deb.py'), '--work-dir', str(work / 'freeze'), '--output-dir', str(work / 'intermediate'), '--stage-only'], check=True)
        source = work / 'freeze/deb-root'
    stage = work / 'payload'
    if stage.exists():
        shutil.rmtree(stage)
    prepare(source.resolve(), stage)
    spec = work / 'wormwright-vault.spec'
    spec.write_text(f'''Name: wormwright-vault
Version: {VERSION}
Release: 1.fc44
Summary: Offline encrypted vault and optional multi-user Manager
License: GPL-3.0-only
URL: https://wormwright.com/vault.html
BuildArch: x86_64
AutoReqProv: no
Requires: glibc >= 2.39, python3, u2f-hidraw-policy
Requires: libgcc, libstdc++, zlib, fontconfig, dbus-libs, glib2
Requires: libdrm.so.2()(64bit)
Requires: libGL.so.1()(64bit), libEGL.so.1()(64bit)
Requires: libX11, libX11-xcb, libXext, libXrender, libxcb
Requires: libxkbcommon, libxkbcommon-x11, xcb-util, xcb-util-cursor
Requires: xcb-util-image, xcb-util-keysyms, xcb-util-renderutil, xcb-util-wm
Requires: libwayland-client.so.0()(64bit), libwayland-cursor.so.0()(64bit), libwayland-egl.so.1()(64bit)
Requires: gvfs-smb, gvfs-fuse
%description
Wormwright Vault with bundled Python and Qt, encrypted local vaults,
shared-folder sync, optional YubiKey unlock and Vault Manager.
Third-party bundled libraries retain their own licenses; see package notices.
%prep
%build
%install
mkdir -p %{{buildroot}}
cp -a "{stage}/usr" %{{buildroot}}/
%files
%defattr(-,root,root,-)
/usr/bin/wormwright-vault
/usr/bin/wormwright-vault-manager
/usr/bin/wormwright-control
/usr/lib64/wormwright-vault
/usr/share/wormwright-vault
/usr/share/applications/wormwright-vault*.desktop
/usr/share/pixmaps/wormwright-vault*.png
%doc /usr/share/doc/wormwright-vault
''')
    subprocess.run([args.rpmbuild, '-bb', '--define', '_topdir ' + str(work / 'rpm'), '--define', '_tmppath ' + str(work), '--define', '_dbpath ' + str(work / 'rpmdb'), '--define', '_rpmdir ' + str(output), '--define', '_build_id_links none', '--define', '__os_install_post %{nil}', '--define', '_binary_payload w2.gzdio', str(spec)], check=True)
    print(output / 'x86_64' / f'wormwright-vault-{VERSION}-1.fc44.x86_64.rpm')


if __name__ == '__main__':
    main()
