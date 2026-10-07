"""Independent rows get safe defaults; competing rows still require a choice."""
import sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from vault import Vault
from sync import configure, synchronize
from conflicts import Comparison
from conflict_dialog import ConflictDialog
application=QApplication([])
with tempfile.TemporaryDirectory() as name:
    root=Path(name); share=root/'share'; share.mkdir()
    a=Vault(root/'a.sqlite'); a.create('dummy-test-password')
    a.save({'description':'Competing','password':'dummy','notes':''})
    a.save({'description':'Independent','password':'dummy2','notes':''})
    configure(a,share,2); synchronize(a)
    b=Vault(root/'b.sqlite'); shutil.copyfile(a.path,b.path); b.unlock('dummy-test-password')
    configure(b,share,2); synchronize(b)
    first,second=a.entries()
    a.save({**first,'notes':'desktop'}); a.save({**second,'notes':'shared change'}); synchronize(a)
    b.save({**first,'notes':'laptop'})
    comparison=Comparison(b); comparison.unlock_shared('dummy-test-password')
    dialog=ConflictDialog(None,comparison)
    assert dialog.choices().count(None)==1 and dialog.choices().count('shared')==1
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Apply).isEnabled()
    for selector in dialog.selectors:
        if selector.currentData() is None: selector.setCurrentIndex(selector.findData('local'))
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Apply).isEnabled()
    comparison.apply(dialog.choices())
    assert {r['notes'] for r in b.entries()}=={'laptop','shared change'}
    dialog.clear_secrets(); comparison.close(); a.lock(); b.lock()
print('Only competing rows require choices; independent shared edits survive conflict resolution.')
