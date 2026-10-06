from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys,tempfile,csv
from pathlib import Path
sys.path.insert(0, str(SOURCE))
from importer import read_export,ImportErrorDetail
from vault import Vault
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder)
 csvfile=root/'export.csv'
 record=dict(description='Test, with comma',link='',user_name='demo',password='demo-secret!',notes='two\nlines')
 with csvfile.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['description','link','user_name','pw','notes'])
  w.writeheader();w.writerow({**{k:v for k,v in record.items() if k!='password'},'pw':record['password']})
 decoded=read_export(csvfile)
 assert decoded==[record]
 v=Vault(root/'vault.sqlite');v.create('test-master-passphrase')
 count,skipped,safety=v.import_records(decoded+decoded)
 assert (count,skipped)==(1,1) and safety.exists()
 previous=Vault(safety);previous.unlock('test-master-passphrase');assert previous.entries()==[];previous.lock()
 assert v.import_records(decoded)==(0,1,None)
 changed={**record,'password':'changed-password'}
 count,skipped,_=v.import_records([changed]);assert count==1 and len(v.entries())==2
 assert b'demo-secret!' not in v.path.read_bytes()
 before=v.entries()
 try: v.import_records([record,dict(description='')]);raise AssertionError()
 except Exception: pass
 assert v.entries()==before
 v.lock()
print('PASS: CSV quoting/newlines, duplicate skipping, safety backup, no overwrites, validation before writes')
