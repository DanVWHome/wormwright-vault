import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent
from app import Window
from preferences import read_timeout, save_timeout
with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_DATA_HOME'] = directory
    assert read_timeout() == 5
    save_timeout(0); assert read_timeout() == 0
    app=QApplication([]); w=Window(Path(directory)/'dummy.sqlite')
    w.vault.create('dummy-test-password'); w.restart_lock_timer()
    assert not w.lock_timer.isActive() and 'Unlimited' in w.lock_status.text()
    w.lock_minutes=2; w.restart_lock_timer()
    assert w.lock_timer.isActive() and w.lock_timer.interval()==120000
    w.lock_timer.start(1000)
    w.eventFilter(w,QEvent(QEvent.Type.KeyPress))
    assert w.lock_timer.interval()==120000
    w.lock(); assert not w.lock_timer.isActive()
    save_timeout(15); assert read_timeout()==15
    w.close()
print('Timeout persistence, Unlimited, idle reset and manual lock checks passed.')
