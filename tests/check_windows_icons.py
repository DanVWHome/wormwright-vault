"""Native Windows executables contain the approved Vault icon at every supplied size."""
from pathlib import Path
import struct,sys
import pefile
root=Path(__file__).resolve().parents[1]
data=(root/'assets/wormwright-vault.ico').read_bytes();reserved,kind,count=struct.unpack_from('<HHH',data);assert (reserved,kind)==(0,1)
expected=[]
for i in range(count):
    size,offset=struct.unpack_from('<II',data,6+16*i+8);expected.append(data[offset:offset+size])
for arg in sys.argv[1:]:
    path=Path(arg);pe=pefile.PE(str(path));embedded=[]
    for resource in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if resource.id!=3:continue # RT_ICON
        for icon in resource.directory.entries:
            for language in icon.directory.entries:
                item=language.data.struct;embedded.append(pe.get_data(item.OffsetToData,item.Size))
    assert all(icon in embedded for icon in expected),f'{path}: approved icon resources missing'
    pe.close();print('PASS embedded Vault icon:',path.name)
