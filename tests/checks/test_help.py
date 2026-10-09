"""Offline help search and optional demo safety checks (Qt offscreen)."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from help_window import HelpWindow
from managed_ui import ManagedWindow
app=QApplication.instance() or QApplication([])
h=HelpWindow();assert h.tree.topLevelItemCount()==7
h.search.setText('dedicated');assert h.tree.topLevelItemCount()>0
h.search.setText('zzznomatch');assert h.tree.topLevelItemCount()==0
with tempfile.TemporaryDirectory() as folder:
    w=ManagedWindow(Path(folder)/'missing.sqlite');w.auto_timer.stop()
    assert not w.vault.path.exists()
    target=Path(folder)/'demo.sqlite'
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(target),'')
    QMessageBox.information=lambda *a,**kw:None
    warnings=[];w.warning=warnings.append
    w.load_demo();assert target.exists() and not w.vault.unlocked
    w.vault.unlock('DemoVault123!','DemoManager');assert len(w.vault.entries(True))==224;w.lock()
    original=target.read_bytes();w.load_demo();assert original==target.read_bytes() and warnings
print('Help and demo safety checks passed')
