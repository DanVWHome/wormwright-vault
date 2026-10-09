from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os,sys,tempfile,threading,socket,json,time
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0, str(SOURCE))
from hooks import LocalControl,send,endpoint
from vault import Vault,VaultError
from search import matching_ids
from app import Window
from PySide6.QtWidgets import QApplication,QLineEdit
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
 os.environ['XDG_RUNTIME_DIR']=folder
 path=folder+'/vault.sqlite'
 w=Window(path);w.vault.create('test-master-passphrase')
 for description,link,notes in [('Gmail','https://mail.google.com','Personal email'),('Other','','Gmail recovery')]:
  w.vault.save(dict(description=description,link=link,notes=notes,password='never-return-this-secret',user_name='username-only-term'))
 records=w.vault.entries()
 assert len(matching_ids(records,'gMaIl'))==2
 assert len(matching_ids(records,'google'))==1
 assert len(matching_ids(records,'recovery'))==1
 assert len(matching_ids(records,'username-only-term'))==2
 assert len(matching_ids(records,'Gm_il'))==2
 assert len(matching_ids(records,"' OR 1=1 --"))==0
 try:w.vault.create('short');raise AssertionError()
 except VaultError:pass
 w.vault.change_password('test-master-passphrase','short')
 w.lock();w.vault.unlock('short');w.update_state();w.refresh()
 request={'version':1,'action':'lookup','query':'Gmail'}
 w.handle_control(request)
 assert w.table.item(w.table.currentRow(),1).text()=='Gmail'
 assert w.table.cellWidget(0,4).findChild(QLineEdit).text()=='••••••••'
 w.lock();w.handle_control(request)
 assert w.pending_lookup=='Gmail' and w.table.rowCount()==0
 w.master.setText('short');w.unlock()
 assert w.table.item(w.table.currentRow(),1).text()=='Gmail'
 service=LocalControl(path,w.handle_control)
 result=[]
 t=threading.Thread(target=lambda: result.append(send(path,request)));t.start()
 while t.is_alive(): service.poll();app.processEvents();time.sleep(.005)
 t.join()
 assert result==[{'version':1,'accepted':True}]
 assert 'never-return-this-secret' not in json.dumps(result)
 try:LocalControl(path,lambda request:None);raise AssertionError('second server allowed')
 except RuntimeError:pass
 # Unsupported actions cannot export or reveal secrets.
 calls=[]
 for action in ['export','unlock','show-password']:
  client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);client.connect(str(endpoint(path)))
  service.poll()  # Connection may arrive before request bytes; must remain open.
  client.sendall(json.dumps({'version':1,'action':action}).encode()+b'\n')
  service.poll()
  assert json.loads(client.recv(1024))['accepted'] is False
  client.close()
 service.close();w.lock()
print('PASS: SQL LIKE search, includes usernames, excludes passwords, short fallback, hidden selection, queued locked lookup, private IPC acknowledgment, single instance, unsupported secret commands rejected')
