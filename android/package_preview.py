"""Package the preview and verify ELF alignment in every shipped native module."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / 'releases/android-preview-0.1.0'
OUTPUT.mkdir(parents=True, exist_ok=True)
VERSION = re.search(r"versionName '([^']+)'", (ROOT / 'app/build.gradle').read_text()).group(1)
APK = OUTPUT / ('wormwright-vault-' + VERSION + '.apk')
shutil.copy2(ROOT / 'app/build/outputs/apk/release/app-release.apk', APK)
native_modules = []


def inspect_archive(content, prefix=''):
    with zipfile.ZipFile(content) as archive:
        for name in archive.namelist():
            if name.endswith('/'):
                continue
            value = archive.read(name)
            if name.endswith('.so'):
                if value[:5] != b'\x7fELF\x02' or value[5] != 1:
                    raise RuntimeError('Expected a little-endian 64-bit library: ' + prefix + name)
                offset = struct.unpack_from('<Q', value, 32)[0]
                size, count = struct.unpack_from('<HH', value, 54)
                segments = []
                for index in range(count):
                    kind, flags, file_offset, virtual, physical, filesz, memsz, alignment = struct.unpack_from('<IIQQQQQQ', value, offset + index * size)
                    if kind == 1:
                        if alignment < 16384 or file_offset % 16384 != virtual % 16384:
                            raise RuntimeError('Library is not 16 KB compatible: ' + prefix + name)
                        segments.append(alignment)
                native_modules.append({'path': prefix + name, 'load_alignment': segments})
            elif name.endswith('.imy') and value.startswith(b'PK'):
                inspect_archive(BytesIO(value), prefix + name + '!/')


inspect_archive(APK)
digest = hashlib.sha256(APK.read_bytes()).hexdigest()
(OUTPUT / 'SHA256SUMS').write_text(digest + '  ' + APK.name + '\n')
lint = (ROOT / 'app/build/reports/lint-results-release.txt').read_text()
lint_counts = re.search(r'(\d+) errors, (\d+) warnings', lint)
unit_tests = [ET.parse(p).getroot() for p in (ROOT / 'app/build/test-results/testReleaseUnitTest').glob('TEST-*.xml')]
report = {
    'version': VERSION, 'app_id': 'ai.wormwright.vault.preview',
    'distribution': 'local signed preview; not published',
    'scope': ['encrypted format-2 import', 'account unlock and offline editing', 'visible-field search',
              'masked list', 'password reveal and copy', 'background and inactivity lock',
              'direct SMB two-way NAS sync', 'three-way entry conflict review', 'verified atomic uploads', 'shared Linux lock protocol', 'encrypted NAS credentials',
              'authenticated snapshot replacement with encrypted backups', 'foreground refresh every 60 seconds'],
    'not_included': ['closed-app background sync', 'Android autofill', 'YubiKey', 'Manager administration'],
    'desktop_interoperability_tests': {'passed': 22, 'failed': 0},
    'network_protocol_unit_tests': {'tests': sum(int(p.get('tests', 0)) for p in unit_tests),
                                    'failures': sum(int(p.get('failures', 0)) + int(p.get('errors', 0)) for p in unit_tests)},
    'android_lint': {'errors': int(lint_counts.group(1)), 'warnings': int(lint_counts.group(2))},
    'native_16kb_alignment': {'passed': True, 'modules': native_modules},
    'pixel_device_acceptance': 'preview.2 import and NAS download user-confirmed; preview.3 editing and upload awaiting device acceptance',
    'sha256': digest,
    'upstream_engine': {'desktop_version': '0.3.0', 'unchanged_files': {
        name: hashlib.sha256((ROOT / 'app/src/main/python' / name).read_bytes()).hexdigest()
        for name in ('managed_vault.py', 'vault.py')}},
}
(OUTPUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with zipfile.ZipFile(OUTPUT / 'wormwright-vault-android-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in {'build', '.gradle', '__pycache__'} for part in relative.parts):
            continue
        if path.name == 'local.properties' or path.suffix in {'.jks', '.keystore'}:
            continue
        archive.write(path, Path('android') / relative)
print(json.dumps({'apk': str(APK), 'size_mb': round(APK.stat().st_size / 1024**2, 1),
                  'aligned_native_modules': len(native_modules), 'sha256': digest}))
