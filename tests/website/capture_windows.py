import os,sys
from pathlib import Path
root=Path.cwd()
if sys.platform != 'win32': os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['XDG_DATA_HOME']=str(root/'work/demo-settings')
sys.path.insert(0,str(root/'src'))
from PySide6.QtWidgets import QApplication,QListWidget
from PySide6.QtCore import QTimer
from managed_ui import ManagedWindow
(root/'screenshots').mkdir(exist_ok=True)
app=QApplication([])
path=root/'screenshots/website-demo.sqlite'
if path.exists():path.unlink()
w=ManagedWindow(path,True);w.auto_timer.stop();w.vault.create('Fictional-demo-manager-only-2026')
labels=['Family','Finance','Home','Work','Travel'];groups={name:w.vault.add_group(name) for name in labels}
for name,gs in [('Alex',['Family','Home','Travel']),('Jamie',['Family','Finance','Home']),('Morgan',['Work','Travel']),('Taylor',['Family','Travel'])]:w.vault.add_user(name,'Fictional-demo-user-only-'+name,[groups[g] for g in gs])
rows=[('Family email','https://mail.example.com','alex@example.com','Family'),('Streaming account','https://stream.example.com','family@example.com','Family'),('Home Wi-Fi','','Home network','Home'),('Front door code','','Main entrance','Home'),('Alarm disarm code','','House alarm','Home'),('Online banking','https://bank.example.com','alex.demo','Finance'),('Savings account number','','Joint savings','Finance'),('Work email','https://work.example.com','morgan@example.com','Work'),('Project dashboard','https://projects.example.com','morgan.demo','Work'),('Travel booking','https://travel.example.com','alex@example.com','Travel'),('Luggage combination','','Blue suitcase','Travel'),('Recovery codes','','Family account','Family'),('Garage keypad','','Side entrance','Home'),('Retired streaming account','https://old.example.com','family@example.com','Family')]
for i,(desc,link,user,group) in enumerate(rows):
 password='Demo-Reused-Password' if i in (0,1) else f'Demo-Only-{i:02d}-Fictional!'
 eid=w.vault.save(dict(description=desc,link=link,user_name=user,password=password,notes='Fictional website demo entry. Not a real credential.',groups=[groups[group]]))
 if i==13:w.vault.delete(eid)
w.update_state();w.refresh();w.resize(1440,820);w.show();app.processEvents();w.table.selectRow(0)
w.status.setText('Unlocked • Fictional demo vault • Website screenshots')
out=root/'screenshots'
w.manager_app=False;w.update_state();w.refresh();w.status.setText('Unlocked • Fictional demo vault • Website screenshots');app.processEvents()
# Create genuine normal Vault view with the shared session.
v=ManagedWindow(path,False);v.auto_timer.stop();v.vault.unlock('Fictional-demo-manager-only-2026','Manager');v.update_state();v.refresh();v.resize(1440,820);v.show();v.status.setText('Unlocked • Fictional demo vault • Website screenshots');app.processEvents();v.table.selectRow(0);v.grab().save(str(out/'windows-vault.png'))
w.manager_app=True;w.update_state();w.show_deleted.setChecked(True);w.refresh();w.status.setText('Unlocked • Fictional demo vault • Website screenshots');app.processEvents();w.grab().save(str(out/'windows-manager.png'))
def capture_groups():
 dialog=app.activeModalWidget()
 if dialog:
  for name in ['management_users','management_groups']:
   widget=dialog.findChild(QListWidget,name)
   if widget:widget.setCurrentRow(0)
  app.processEvents();dialog.grab().save(str(out/'windows-groups.png'));dialog.accept()
QTimer.singleShot(150,capture_groups);w.manage()
for window in [w,v]:window.close_ready=True;window.close()
print('Captured real Windows UI with 14 fictional entries and four demo users.')
