"""Check manifest identity, permissions, APK ZIP and all nested ELF alignment."""
import io,json,struct,subprocess,sys,zipfile
from pathlib import Path
apk=Path(sys.argv[1]);sdk=Path(sys.argv[2]);elf=[];issues=[]
def inspect(data,name):
    if data[:4]==b'\x7fELF':
        if data[4]!=2 or data[5]!=1:issues.append(name+': unsupported ELF');return
        offset=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
        aligns=[]
        for i in range(count):
            header=struct.unpack_from('<IIQQQQQQ',data,offset+i*size)
            if header[0]==1:
                aligns.append(header[7])
                if header[7]<16384:issues.append(name+': PT_LOAD alignment '+str(header[7]))
        elf.append({'path':name,'load_alignments':aligns})
    elif data[:4]==b'PK\x03\x04':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if not member.is_dir():inspect(archive.read(member),name+'!'+member.filename)
with zipfile.ZipFile(apk) as archive:
    for member in archive.infolist():
        if not member.is_dir():inspect(archive.read(member),member.filename)
output=subprocess.check_output([str(sdk/'build-tools/36.0.0/aapt'),'dump','badging',str(apk)],text=True)
assert "package: name='ai.wormwright.vault.standalone'" in output
assert "targetSdkVersion:'36'" in output
assert 'android.permission.INTERNET' not in output
assert 'android.permission.USE_BIOMETRIC' in output
subprocess.run([str(sdk/'build-tools/36.0.0/zipalign'),'-c','-P','16','-v','4',str(apk)],check=True,stdout=subprocess.DEVNULL)
subprocess.run([str(sdk/'build-tools/36.0.0/apksigner'),'verify',str(apk)],check=True)
report={'package':'ai.wormwright.vault.standalone','target_api':36,'permissions':['USE_BIOMETRIC'],'elf_libraries':elf,'issues':issues,'device_runtime_test':'pending'}
print(json.dumps(report,indent=2))
if issues:sys.exit(1)
