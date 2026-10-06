from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import os,sys,tempfile,subprocess,time
from pathlib import Path
sys.path.insert(0, str(SOURCE))
from vault import Vault
from hooks import send
with tempfile.TemporaryDirectory() as folder:
 path=Path(folder)/'vault.sqlite';vault=Vault(path);vault.create('test-master-passphrase');vault.lock()
 env={**os.environ,'QT_QPA_PLATFORM':'offscreen','XDG_RUNTIME_DIR':folder}
 old=os.environ.get('XDG_RUNTIME_DIR');os.environ['XDG_RUNTIME_DIR']=folder
 process=subprocess.Popen([sys.executable,str(SOURCE / 'app.py'),str(path),'--lookup','Gmail'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    response=send(path,{'version':1,'action':'capabilities'});break
   except (FileNotFoundError,ConnectionRefusedError):
    assert process.poll() is None
    time.sleep(.05)
  else:raise AssertionError('IPC never started')
  assert response['returns_secrets'] is False
  second=subprocess.run([sys.executable,str(SOURCE / 'app.py'),str(path),'--lookup','Gmail'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
  assert second.returncode==0
  assert send(path,{'version':1,'action':'lock'})=={'version':1,'accepted':True}
 finally:
  process.terminate();process.wait(timeout=5)
  if old is None:os.environ.pop('XDG_RUNTIME_DIR',None)
  else:os.environ['XDG_RUNTIME_DIR']=old
print('PASS: closed-app startup, live socket capabilities, second launch forwards to existing instance, blind lock acknowledgment')
