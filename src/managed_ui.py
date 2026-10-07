"""Managed-format UI shared by Vault and the optional Vault Manager launcher."""
from pathlib import Path
import sys
import tempfile
import shutil
from collections import Counter
from PySide6.QtCore import Qt,QTimer,QThread,QEvent
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,
    QDialog,QDialogButtonBox,QFormLayout,QTextEdit,QMessageBox,QFileDialog,QCheckBox,QListWidget,
    QListWidgetItem,QInputDialog,QSpinBox,QMenu,QComboBox,QSplitter)
from managed_vault import ManagedVault,is_managed,convert_personal
from managed_sync import synchronize,state,combined,snapshot,reconcile
from vault import VaultError
from sync import read_settings,configure,SyncConflict
from preferences import read_timeout,save_timeout
from history import VaultHistory
from search import matching_ids
from exporter import export_csv
from importer import read_export
from version import VERSION
import managed_locations


class SyncTask(QThread):
    def __init__(self,path,session,choices=None,expected=None):
        super().__init__();self.path=path;self.session=session;self.choices=choices;self.expected=expected
        self.result=None;self.error=None;self.conflict=False
    def run(self):
        try:self.result=synchronize(self.path,self.session,self.choices,self.expected)
        except Exception as error:self.error=str(error);self.conflict=isinstance(error,SyncConflict)
        finally:self.session=None


def groups_list(labels,selected):
    widget=QListWidget()
    for gid,name in labels.items():
        item=QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole,gid)
        item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if gid in selected else Qt.CheckState.Unchecked)
        widget.addItem(item)
    widget.setMaximumHeight(140)
    return widget


def selected_groups(widget):
    return [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())
            if widget.item(i).checkState()==Qt.CheckState.Checked]


class ManagedWindow(QMainWindow):
    def __init__(self,path,manager_app=False):
        super().__init__()
        self.vault=ManagedVault(path);self.manager_app=manager_app;self.records=[];self.pending_lookup=None
        self.dialog=None;self.key_task=None;self.password_display=None;self.clipboard_value=None;self.task=None
        self.again=False;self.closing=False;self.conflicted=False;self.manual=False
        self.history=VaultHistory();self.lock_minutes=read_timeout();self.password_fallback=False
        self.setWindowTitle(f'Wormwright Vault{" Manager" if manager_app else ""} {VERSION} — Managed test build')
        self.resize(1160,700)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        logo=QHBoxLayout();icon=QLabel();asset=Path(getattr(sys,'_MEIPASS',Path(__file__).parent.parent))/'assets'/('wormwright-vault-manager.png' if manager_app else 'wormwright-vault.png')
        if asset.exists():
            self.setWindowIcon(QIcon(str(asset)));icon.setPixmap(QPixmap(str(asset)).scaled(56,56,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));logo.addWidget(icon)
        title=QLabel('Wormwright Vault Manager' if manager_app else 'Wormwright Vault');title.setStyleSheet('font-size:26px;font-weight:bold')
        logo.addWidget(title);logo.addStretch();layout.addLayout(logo)
        layout.addWidget(QLabel(f'Version {VERSION} • Managed test build'))
        self.status=QLabel();layout.addWidget(self.status)
        folder_row=QHBoxLayout();self.folder_label=QLabel();self.folder_label.setWordWrap(True);folder_row.addWidget(self.folder_label,1)
        self.folder_button=QPushButton('Choose Folder…');self.folder_button.clicked.connect(self.choose_folder);folder_row.addWidget(self.folder_button);layout.addLayout(folder_row)
        location_help=QLabel('This device keeps its working vault locally. Vaults can be stored outside the default folder. The optional shared NAS folder is configured separately in Sync Settings.');location_help.setWordWrap(True);layout.addWidget(location_help)
        login=QHBoxLayout();self.username=QLineEdit();self.username.setPlaceholderText('Username');self.username.setObjectName('vault_username')
        self.master=QLineEdit();self.master.setEchoMode(QLineEdit.EchoMode.Password);self.master.setPlaceholderText('Account password')
        login.addWidget(self.username);login.addWidget(self.master)
        self.unlock_button=QPushButton('Unlock / Create Vault');self.unlock_button.clicked.connect(self.unlock);login.addWidget(self.unlock_button)
        self.key_button=QPushButton('YubiKey — PIN + Touch');self.key_button.clicked.connect(self.unlock_key);login.addWidget(self.key_button)
        self.fallback=QPushButton('Use Password');self.fallback.clicked.connect(self.show_fallback);login.addWidget(self.fallback)
        self.username.textChanged.connect(self.update_state);self.master.returnPressed.connect(self.unlock)
        layout.addLayout(login)
        self.welcome=QWidget();welcome_layout=QVBoxLayout(self.welcome)
        heading=QLabel('Welcome — choose how to get started');heading.setStyleSheet('font-size:20px;font-weight:bold');welcome_layout.addWidget(heading)
        help_text=QLabel('Create a new vault to start from scratch. Open a local copy of an existing new-format vault, or convert an older personal vault into a separate copy. Your original vault is preserved.');help_text.setWordWrap(True);welcome_layout.addWidget(help_text)
        welcome_row=QHBoxLayout()
        for text,callback in [('Create New Vault…',self.new_vault),('Open Existing Vault…',self.open_existing),('Convert Personal Vault…',self.convert)]:
            b=QPushButton(text);b.clicked.connect(callback);welcome_row.addWidget(b)
        welcome_layout.addLayout(welcome_row);layout.addWidget(self.welcome)
        self.location_row=QWidget();row=QHBoxLayout(self.location_row);row.setContentsMargins(0,0,0,0)
        for text,callback in [('Open Existing Vault…',self.open_existing),('Create New Vault…',self.new_vault),('Recent Vaults…',self.recent),('Convert Personal Vault…',self.convert)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
        layout.addWidget(self.location_row)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search description, link or notes');self.search.textChanged.connect(self.refresh);row.addWidget(self.search)
        self.controls=[]
        for text,callback in [('Add',self.add),('Edit',self.edit),('Clone',self.clone),('Delete',self.delete),('Lock',self.lock)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button);self.controls.append(button)
        copy=QPushButton('Copy Field');menu=QMenu(copy)
        for field,label in [('description','Description'),('link','Link'),('user_name','User Name'),('password','Password'),('notes','Notes')]:
            menu.addAction(label,lambda checked=False,f=field:self.copy_field(f))
        copy.setMenu(menu);row.addWidget(copy);self.controls.append(copy);layout.addLayout(row)
        row=QHBoxLayout()
        for text,callback in [('Import Vault CSV…',self.import_entries),('Export to CSV…',self.export),('Back Up Vault…',self.backup),('Restore Backup…',self.restore_backup),('Sync Settings…',self.sync_settings),('Sync Now',self.sync_now),('Lock Settings…',self.lock_settings),('Set Up YubiKey…',self.enroll),('Change Password…',self.change_password)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
            if text not in ('Sync Now','Sync Settings…','Lock Settings…'):self.controls.append(button)
        layout.addLayout(row)
        self.manager_row=QWidget();row=QHBoxLayout(self.manager_row);row.setContentsMargins(0,0,0,0)
        self.show_deleted=QCheckBox('Show deleted entries');self.show_deleted.setObjectName('show_deleted');self.show_deleted.toggled.connect(self.refresh);row.addWidget(self.show_deleted)
        for text,callback in [('Users & Groups…',self.manage),('Individual Exclusions…',self.exclusions),('Restore Entry',self.restore_entry),('Permanently Delete…',self.purge)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
        layout.addWidget(self.manager_row)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['Description','Link','User Name','Password','Groups','Status','Duplicate Password'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);self.table.setColumnWidth(3,240)
        self.table.cellDoubleClicked.connect(self.edit);layout.addWidget(self.table)
        self.sync_status=QLabel('Sync not configured.');layout.addWidget(self.sync_status)
        layout.addWidget(QLabel('Clipboard clears after 30 seconds • Deleted entries are visible only to the Manager'))
        self.clipboard_timer=QTimer(self);self.clipboard_timer.setSingleShot(True);self.clipboard_timer.timeout.connect(self.clear_clipboard)
        self.lock_timer=QTimer(self);self.lock_timer.setSingleShot(True);self.lock_timer.timeout.connect(self.lock)
        self.auto_timer=QTimer(self);self.auto_timer.timeout.connect(self.auto_sync);self.auto_timer.start(self.interval())
        QApplication.instance().installEventFilter(self)
        self.update_state();QTimer.singleShot(0,self.auto_sync)

    def warning(self,error):QMessageBox.warning(self,'Wormwright Vault',str(error))

    def interval(self):
        try:return int(read_settings(self.vault).get('interval',30))*1000
        except Exception:return 30000

    def touch(self):
        if self.vault.unlocked and self.lock_minutes:self.lock_timer.start(self.lock_minutes*60000)

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.MouseButtonPress,QEvent.Type.Wheel):self.touch()
        return super().eventFilter(obj,event)

    def update_state(self):
        unlocked=self.vault.unlocked
        self.folder_label.setText('Local folder for new vaults: '+str(managed_locations.local_folder()));self.folder_button.setEnabled(not self.task)
        missing=not self.vault.path.exists();self.welcome.setVisible(missing);self.location_row.setVisible(not missing)
        self.status.setText(f'{"Unlocked" if unlocked else "Locked"} • {self.vault.path}')
        try:personal=self.vault.personal;has_key=self.vault.yubikey_settings(self.username.text()) is not None
        except Exception:personal=True;has_key=False
        self.username.setVisible(not unlocked and not personal)
        password_visible=not unlocked and (not has_key or self.password_fallback)
        self.master.setVisible(password_visible and not missing);self.unlock_button.setVisible(password_visible and not missing);self.unlock_button.setText('Unlock Vault')
        self.key_button.setVisible(not unlocked and has_key);self.fallback.setVisible(not unlocked and has_key and not self.password_fallback)
        self.manager_row.setVisible(self.vault.manager);self.search.setEnabled(unlocked)
        for button in self.controls:button.setEnabled(unlocked and not self.task)

    def show_fallback(self):self.password_fallback=True;self.update_state()

    def password_prompt(self,label='Current account password:'):
        dialog=QInputDialog(self);dialog.setWindowTitle('Authenticate');dialog.setLabelText(label);dialog.setTextEchoMode(QLineEdit.EchoMode.Password);dialog.resize(560,160);dialog.setMinimumWidth(520)
        try:
            accepted=dialog.exec()==QDialog.DialogCode.Accepted
            return dialog.textValue(),accepted
        finally:dialog.setTextValue('');dialog.deleteLater()

    def new_password(self,title,minimum=False):
        dialog=QDialog(self);dialog.setWindowTitle(title);dialog.resize(600,220);dialog.setMinimumWidth(560);form=QFormLayout(dialog)
        password=QLineEdit();password.setEchoMode(QLineEdit.EchoMode.Password)
        confirmation=QLineEdit();confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Password (12+ characters):' if minimum else 'New password:',password);form.addRow('Confirm password:',confirmation)
        error=QLabel();form.addRow(error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);form.addRow(buttons)
        def accept():
            if not password.text() or (minimum and len(password.text())<12):error.setText('Enter at least 12 characters.' if minimum else 'Enter a password.')
            elif password.text()!=confirmation.text():error.setText('Passwords do not match.')
            else:dialog.accept()
        buttons.accepted.connect(accept);buttons.rejected.connect(dialog.reject)
        previous_dialog=self.dialog;self.dialog=dialog
        try:return password.text() if dialog.exec()==QDialog.DialogCode.Accepted else None
        finally:password.clear();confirmation.clear();self.dialog=previous_dialog;dialog.deleteLater()

    def create_account(self,path=None):
        path=Path(path) if path is not None else self.vault.path
        dialog=QDialog(self);dialog.setWindowTitle('Create New Vault');dialog.resize(640,300);dialog.setMinimumWidth(580);form=QFormLayout(dialog)
        explanation=QLabel('Choose your own Manager name and an initial master password. This account can access every group. You can add other users later in Users & Groups.');explanation.setWordWrap(True);form.addRow(explanation)
        name=QLineEdit();name.setPlaceholderText('Your name, for example Dan')
        password=QLineEdit();password.setEchoMode(QLineEdit.EchoMode.Password)
        confirm=QLineEdit();confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Manager username:',name);form.addRow('Master password (12+ characters):',password);form.addRow('Confirm master password:',confirm)
        location=QLabel('Save local vault to: '+str(path));location.setWordWrap(True);form.addRow(location)
        error=QLabel();form.addRow(error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);form.addRow(buttons)
        def accept():
            if not name.text().strip():error.setText('Enter your Manager username.')
            elif len(password.text())<12:error.setText('Enter at least 12 characters.')
            elif password.text()!=confirm.text():error.setText('Passwords do not match.')
            else:dialog.accept()
        buttons.accepted.connect(accept);buttons.rejected.connect(dialog.reject)
        previous=self.dialog;self.dialog=dialog
        try:
            if dialog.exec()!=QDialog.DialogCode.Accepted:return False
            manager_name=name.text().strip();candidate=ManagedVault(path);candidate.create(password.text(),manager_name)
            self.dialog=previous;self.lock();self.vault=candidate;self.username.setText(manager_name);self.search.clear();self.password_fallback=False
            managed_locations.remember(folder=path.parent,vault=path);return True
        finally:password.clear();confirm.clear();self.dialog=previous;dialog.deleteLater()

    def unlock(self):
        if self.task:return
        try:
            if not self.vault.path.exists():
                self.new_vault();return
            self.vault.unlock(self.master.text(),self.username.text())
            self.master.clear();self.history.remember(self.vault.path);managed_locations.remember(vault=self.vault.path);self.touch();self.update_state();self.refresh()
            self.complete_lookup();self.auto_sync()
            # Keep the main vault visible after unlock; management is an explicit action.
        except Exception as error:self.warning(error);self.update_state()

    def selected(self):
        row=self.table.currentRow()
        return self.records[row] if 0<=row<len(self.records) else None

    def refresh(self,*args):
        self.close_display();self.records=[];self.table.setRowCount(0)
        if not self.vault.unlocked:return
        try:
            records=self.vault.entries(include_deleted=self.vault.manager and self.show_deleted.isChecked())
            ids=set(matching_ids(records,self.search.text())) if self.search.text() else {r['id'] for r in records}
            self.records=[r for r in records if r['id'] in ids]
            counts=Counter(r['password'] for r in records if r.get('password'))
            self.table.setRowCount(len(self.records))
            for i,record in enumerate(self.records):
                values=[record['description'],record.get('link',''),record.get('user_name',''),'••••••••',
                    ', '.join(self.vault.available_groups().get(g,'Shared group') for g in record['groups']),
                    'Deleted' if record.get('deleted') else '',f'Used in {counts[record["password"]]} entries' if counts[record.get('password','')]>1 else '']
                for j,value in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(value))
                widget=QWidget();row=QHBoxLayout(widget);row.setContentsMargins(2,0,2,0);row.addWidget(QLabel('••••••••'))
                for text,callback in [('Show',lambda checked=False,r=record:self.reveal(r)),('Copy',lambda checked=False,r=record:self.copy_text(r['password']))]:
                    button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
                self.table.setCellWidget(i,3,widget)
            if self.records:self.table.selectRow(0)
        except Exception as error:self.lock();self.warning(error)

    def edit_record(self,record=None):
        if not self.vault.unlocked or self.task:return
        from app import EntryDialog
        dialog=EntryDialog(self,record);self.dialog=dialog
        group_widget=None
        if self.vault.manager or not record or not record.get('id'):
            labels=self.vault.available_groups()
            defaults=record.get('groups',list(labels)[:1]) if record else [g for g,n in labels.items() if n=='Generic'] or list(labels)[:1]
            group_widget=groups_list(labels,defaults);dialog.layout().insertWidget(1,QLabel('Groups:'));dialog.layout().insertWidget(2,group_widget)
        try:
            if dialog.exec()==QDialog.DialogCode.Accepted and self.vault.unlocked:
                value=dialog.value()
                if group_widget:value['groups']=selected_groups(group_widget)
                self.vault.save(value);self.refresh();self.auto_sync()
        except Exception as error:self.warning(error)
        finally:
            for field in dialog.fields.values():field.clear()
            dialog.notes.clear();dialog.record.clear();self.dialog=None;dialog.deleteLater()
            if self.again:QTimer.singleShot(0,self.auto_sync)

    def add(self):self.edit_record()
    def edit(self,*args):
        if self.selected():self.edit_record(self.selected())
    def clone(self):
        if self.selected():
            record={k:v for k,v in self.selected().items() if k in ('description','link','user_name','password','notes')}
            self.edit_record(record)
    def delete(self):
        record=self.selected()
        if record and not self.task and QMessageBox.question(self,'Hide entry','Mark this entry as deleted? The Manager can restore it.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            try:self.vault.delete(record['id']);self.refresh();self.auto_sync()
            except Exception as error:self.warning(error)
    def restore_entry(self):
        if self.selected() and self.vault.manager:
            try:self.vault.restore_entry(self.selected()['id']);self.refresh();self.auto_sync()
            except Exception as error:self.warning(error)
    def purge(self):
        record=self.selected()
        if not record or not self.vault.manager or self.task:return
        if QMessageBox.question(self,'Permanently delete entry','Remove this record from the database permanently? Existing backups may retain it. This cannot be undone in the current vault.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        password,ok=self.password_prompt()
        if not ok:return
        try:self.vault.verify_password(password);self.vault.purge(record['id']);self.refresh();self.auto_sync()
        except Exception as error:self.warning(error)

    def copy_text(self,value):
        if not self.vault.unlocked:return
        self.clipboard_value=value;QApplication.clipboard().setText(value);self.clipboard_timer.start(30000)
    def copy_field(self,field):
        if self.selected():self.copy_text(self.selected().get(field,''))
    def clear_clipboard(self):
        if self.clipboard_value is not None and QApplication.clipboard().text()==self.clipboard_value:QApplication.clipboard().clear()
        self.clipboard_value=None
    def reveal(self,record):
        from app import PasswordDisplay
        if self.vault.unlocked:
            self.close_display();self.password_display=PasswordDisplay(self,record);self.password_display.show()
    def close_display(self):
        if self.password_display:self.password_display.reject();self.password_display.deleteLater();self.password_display=None
    def lock(self):
        self.close_display();self.clear_clipboard();self.lock_timer.stop();self.master.clear();self.records=[];self.table.setRowCount(0);self.pending_lookup=None
        if self.key_task:self.key_task.cancelled.set()
        for dialog in self.findChildren(QDialog):
            dialog.reject()
            for field in dialog.findChildren(QLineEdit):field.clear()
            for field in dialog.findChildren(QTextEdit):field.clear()
        self.vault.lock();self.update_state()
    def handle_control(self,request):
        if request['action']=='lock':self.lock()
        else:
            if request['action']=='lookup':self.pending_lookup=request['query']
            self.complete_lookup();self.showNormal();self.raise_();self.activateWindow()
    def complete_lookup(self):
        if self.vault.unlocked and self.pending_lookup is not None:
            query=self.pending_lookup;self.pending_lookup=None;self.search.setText(query);self.refresh()

    def choose_folder(self):
        if self.task:return
        folder=QFileDialog.getExistingDirectory(self,'Choose local folder for new vaults',str(managed_locations.local_folder()))
        if folder:
            managed_locations.remember(folder=folder);self.update_state()

    def new_vault(self):
        if self.task:return
        path,_=QFileDialog.getSaveFileName(self,'Save new local vault',str(managed_locations.local_folder()/'vault.sqlite'),'SQLite vault (*.sqlite)',options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:return
        destination=Path(path)
        if not destination.suffix:destination=destination.with_suffix('.sqlite')
        if destination.exists():self.warning('That file already exists. Open it using Open Existing Vault, or choose a new filename.');return
        try:
            if not self.create_account(destination):return
            self.master.clear();self.history.remember(self.vault.path);self.touch();self.update_state();self.refresh();self.complete_lookup();self.auto_sync()
        except Exception as error:self.warning(error);self.update_state()

    def open_existing(self):
        if self.task:return
        path,_=QFileDialog.getOpenFileName(self,'Open existing local vault',str(managed_locations.local_folder()),'SQLite vault (*.sqlite)')
        if path:self.open_path(Path(path))

    def choose(self):
        if self.task:return
        path,_=QFileDialog.getSaveFileName(self,'Choose or create local vault',str(self.vault.path),'SQLite vault (*.sqlite)',options=QFileDialog.Option.DontConfirmOverwrite)
        if path:self.open_path(Path(path))
    def open_path(self,path):
        if path.resolve()==self.vault.path.resolve():return
        if path.exists() and not is_managed(path):
            QMessageBox.information(self,'Personal vault','This is a legacy personal vault. Use Convert Personal Vault to create a new-format copy; the original stays usable.');return
        self.lock();self.vault=ManagedVault(path);self.username.clear();self.search.clear();self.password_fallback=False;self.update_state()
    def recent(self):
        dialog=QDialog(self);dialog.setWindowTitle('Recent Vaults');layout=QVBoxLayout(dialog);items=QListWidget();items.addItems(self.history.read());layout.addWidget(items)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Open|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()==QDialog.DialogCode.Accepted and items.currentItem() and not self.task:self.open_path(Path(items.currentItem().text()))
        dialog.deleteLater()
    def convert(self):
        if self.task:return
        source,_=QFileDialog.getOpenFileName(self,'Select personal vault to convert','','SQLite vault (*.sqlite)')
        if not source:return
        if is_managed(source):self.warning('This vault already uses the new format.');return
        destination,_=QFileDialog.getSaveFileName(self,'Save converted copy',str(Path(source).with_name(Path(source).stem+'-managed.sqlite')),'SQLite vault (*.sqlite)')
        if not destination:return
        password,ok=self.password_prompt('Personal vault password:')
        if not ok:return
        username,ok=QInputDialog.getText(self,'Manager account','Your Manager username:',text='Manager')
        if not ok:return
        try:
            needs_key=convert_personal(source,destination,password,username)
            self.open_path(Path(destination));self.master.setText(password);self.unlock()
            if needs_key:QMessageBox.information(self,'YubiKey enrollment','The original vault and its YubiKey enrollment are unchanged. Enroll your YubiKey for the converted copy using Set Up YubiKey.')
        except Exception as error:self.warning(error)

    def manage(self):
        if not self.vault.manager or self.task:return
        dialog=QDialog(self);dialog.setWindowTitle('Wormwright Vault Manager — Users & Groups');dialog.resize(900,540);layout=QVBoxLayout(dialog)
        splitter=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(splitter)
        user_panel=QWidget();user_layout=QVBoxLayout(user_panel);user_layout.addWidget(QLabel('Users'))
        users=QListWidget();users.setObjectName('management_users');user_layout.addWidget(users)
        user_details=QLabel('Select a user to see their groups.');user_details.setWordWrap(True);user_layout.addWidget(user_details)
        group_panel=QWidget();group_layout=QVBoxLayout(group_panel);group_layout.addWidget(QLabel('Groups'))
        groups=QListWidget();groups.setObjectName('management_groups');group_layout.addWidget(groups)
        group_details=QLabel('Select a group to see its members and entry counts.');group_details.setWordWrap(True);group_layout.addWidget(group_details)
        splitter.addWidget(user_panel);splitter.addWidget(group_panel);splitter.setSizes([480,360])
        def show_user():
            item=users.currentItem()
            if not item:user_details.setText('Select a user to see their groups.');return
            uid=item.data(Qt.ItemDataRole.UserRole);admin=self.vault.administration()
            names=sorted(g['name'] for g in admin['groups'].values() if uid in g['members'])
            user_details.setText('Groups: '+(', '.join(names) or 'None')+'\nIndividual exclusions can further restrict access.')
        def show_group():
            item=groups.currentItem()
            if not item:group_details.setText('Select a group to see its members and entry counts.');return
            gid=item.data(Qt.ItemDataRole.UserRole);admin=self.vault.administration();group=admin['groups'][gid]
            names=sorted(admin['users'][uid]['identity']['name']+(' [disabled]' if admin['users'][uid]['identity']['disabled'] else '') for uid in group['members'])
            records=[r for r in self.vault.entries(True) if gid in r['groups']]
            active=sum(not r.get('deleted',False) for r in records)
            group_details.setText('Members: '+(', '.join(names) or 'None')+f'\nEntries: {active} active, {len(records)-active} deleted.\nEntries may belong to multiple groups.')
        def populate():
            selected_uid=users.currentItem().data(Qt.ItemDataRole.UserRole) if users.currentItem() else None
            selected_gid=groups.currentItem().data(Qt.ItemDataRole.UserRole) if groups.currentItem() else None
            users.clear();groups.clear();admin=self.vault.administration()
            for uid,data in sorted(admin['users'].items(),key=lambda pair:pair[1]['identity']['name'].casefold()):
                identity=data['identity'];names=sorted(g['name'] for g in admin['groups'].values() if uid in g['members'])
                item=QListWidgetItem(identity['name']+' — '+', '.join(names)+(' [disabled]' if identity['disabled'] else '')+(' [Manager]' if uid==self.vault.uid else ''))
                item.setData(Qt.ItemDataRole.UserRole,uid);users.addItem(item)
                if uid==selected_uid:users.setCurrentItem(item)
            for gid,data in sorted(admin['groups'].items(),key=lambda pair:pair[1]['name'].casefold()):
                item=QListWidgetItem(data['name']+f" — {len(data['members'])} members")
                item.setData(Qt.ItemDataRole.UserRole,gid);groups.addItem(item)
                if gid==selected_gid:groups.setCurrentItem(item)
            show_user();show_group()
        users.currentItemChanged.connect(show_user);groups.currentItemChanged.connect(show_group)
        def action(callback):
            try:callback();populate();self.update_state();self.refresh();self.again=True
            except Exception as error:self.warning(error)
        def add_group():
            name,ok=QInputDialog.getText(dialog,'New group','Group name:')
            if ok:self.vault.add_group(name)
        def user_form():
            form_dialog=QDialog(dialog);form_dialog.setWindowTitle('Add User');form_dialog.resize(600,420);form_dialog.setMinimumWidth(560);form=QFormLayout(form_dialog)
            name=QLineEdit();password=QLineEdit();password.setEchoMode(QLineEdit.EchoMode.Password);confirm=QLineEdit();confirm.setEchoMode(QLineEdit.EchoMode.Password)
            labels=self.vault.available_groups();choices=groups_list(labels,[g for g,n in labels.items() if n=='Generic'])
            form.addRow('Username:',name);form.addRow('Password:',password);form.addRow('Confirm:',confirm);form.addRow('Groups:',choices)
            warning=QLabel('Group members receive entries in those groups. Review the access list before creating the account.');warning.setWordWrap(True);form.addRow(warning)
            buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);form.addRow(buttons);buttons.accepted.connect(form_dialog.accept);buttons.rejected.connect(form_dialog.reject)
            try:
                if form_dialog.exec()!=QDialog.DialogCode.Accepted:return
                if password.text()!=confirm.text():raise VaultError('Passwords do not match.')
                gids=selected_groups(choices)
                records=[r for r in self.vault.entries() if set(gids)&set(r['groups'])]
                preview='\n'.join(r['description'] for r in records) or '(No current entries)'
                if QMessageBox.question(dialog,'Review sharing','This user will receive these entries through their groups:\n\n'+preview+'\n\nCreate this account?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                    self.vault.add_user(name.text(),password.text(),gids)
            finally:password.clear();confirm.clear();form_dialog.deleteLater()
        def selected_user():
            if not users.currentItem():raise VaultError('Select a user.')
            return users.currentItem().data(Qt.ItemDataRole.UserRole)
        def memberships():
            uid=selected_user()
            if uid==self.vault.uid:
                QMessageBox.information(dialog,'Manager groups','The Manager is automatically assigned to every group and cannot be unassigned.');return
            admin=self.vault.administration();choices=groups_list(self.vault.available_groups(),[g for g,data in admin['groups'].items() if uid in data['members']])
            d=QDialog(dialog);d.setWindowTitle('Assign User Groups');l=QVBoxLayout(d);l.addWidget(QLabel('Changes affect access to existing entries. Creators retain their own entries unless excluded.'));l.addWidget(choices)
            buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);l.addWidget(buttons);buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject)
            if d.exec()==QDialog.DialogCode.Accepted:self.vault.set_memberships(uid,selected_groups(choices))
            d.deleteLater()
        def rename_manager():
            current=self.vault.administration()['users'][self.vault.uid]['identity']['name']
            name,ok=QInputDialog.getText(dialog,'Rename Manager','Manager username:',text=current)
            if ok:self.vault.rename_manager(name);self.username.setText(name.strip())
        def reset():
            uid=selected_user();password=self.new_password('Reset account password')
            if password is not None:self.vault.reset_password(uid,password)
        def disable():
            uid=selected_user();identity=self.vault.administration()['users'][uid]['identity'];self.vault.set_disabled(uid,not identity['disabled'])
        for buttons in [[('Add User…',user_form),('Assign Groups…',memberships)], [('Reset Password…',reset),('Disable / Enable',disable)]]:
            row=QHBoxLayout()
            for text,callback in buttons:
                b=QPushButton(text);b.clicked.connect(lambda checked=False,f=callback:action(f));row.addWidget(b)
            user_layout.addLayout(row)
        rename=QPushButton('Rename Manager…');rename.clicked.connect(lambda:action(rename_manager));user_layout.addWidget(rename)
        add=QPushButton('Add Group…');add.clicked.connect(lambda:action(add_group));group_layout.addWidget(add)
        close=QPushButton('Close');close.clicked.connect(dialog.accept);layout.addWidget(close)
        populate();self.dialog=dialog;dialog.exec();self.dialog=None;dialog.deleteLater();self.auto_sync()

    def exclusions(self):
        if not self.vault.manager or self.task:return
        admin=self.vault.administration();dialog=QDialog(self);dialog.setWindowTitle('Individual exclusions');layout=QVBoxLayout(dialog)
        users=QComboBox()
        for uid,data in admin['users'].items():
            if uid!=self.vault.uid:users.addItem(data['identity']['name'],uid)
        if not users.count():self.warning('Create an ordinary user first.');dialog.deleteLater();return
        layout.addWidget(QLabel('Checked entries are excluded, even through group membership or creation.'));layout.addWidget(users)
        records=self.vault.entries(True);items=QListWidget();layout.addWidget(items)
        def fill():
            items.clear();uid=users.currentData()
            for record in records:
                item=QListWidgetItem(record['description']+(' [Deleted]' if record.get('deleted') else ''));item.setData(Qt.ItemDataRole.UserRole,record['id']);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if any(r['entry']==record['id'] and r['user']==uid for r in admin['exclusions']) else Qt.CheckState.Unchecked);items.addItem(item)
        users.currentIndexChanged.connect(fill);fill()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        self.dialog=dialog
        try:
            if dialog.exec()==QDialog.DialogCode.Accepted:
                uid=users.currentData()
                for i in range(items.count()):
                    item=items.item(i);eid=item.data(Qt.ItemDataRole.UserRole);excluded=item.checkState()==Qt.CheckState.Checked
                    old=any(r['entry']==eid and r['user']==uid for r in admin['exclusions'])
                    if excluded!=old:self.vault.set_excluded(eid,uid,excluded)
                self.refresh()
        except Exception as error:self.warning(error)
        finally:self.dialog=None;dialog.deleteLater();self.auto_sync()

    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Back up encrypted vault','','SQLite vault (*.sqlite)')
        if path:
            try:self.vault.backup(path)
            except Exception as error:self.warning(error)
    def restore_backup(self):
        if not self.vault.manager or self.task:
            self.warning('Only the Manager may restore a whole-vault backup.');return
        if QMessageBox.warning(self,'Restore Backup','Restoring also restores old account credentials, memberships and exclusions. Previously revoked access may return. Save the current copy and continue?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        current,ok=self.password_prompt()
        if not ok:return
        try:
            self.vault.verify_password(current)
            source,_=QFileDialog.getOpenFileName(self,'Choose encrypted backup','','SQLite vault (*.sqlite)')
            if not source:return
            username,ok=QInputDialog.getText(self,'Backup Manager','Manager username in the backup:',text='Manager')
            if not ok:return
            password,ok=self.password_prompt('Backup Manager password:')
            if not ok:return
            self.vault.restore(source,password,username);self.update_state();self.refresh();self.auto_sync()
        except Exception as error:self.warning(error)

    def export(self):
        password,ok=self.password_prompt()
        if not ok:return
        path,_=QFileDialog.getSaveFileName(self,'Export visible active entries to plaintext CSV','','CSV (*.csv)')
        if path:
            try:export_csv(self.vault,path,password=password)
            except Exception as error:self.warning(error)
    def import_entries(self):
        path,_=QFileDialog.getOpenFileName(self,'Import Vault CSV','','CSV (*.csv)')
        if not path:return
        try:
            records=read_export(path)
            if QMessageBox.question(self,'Import entries',f'Import {len(records)} entries into your default group(s)?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            safety=self.vault.path.with_name(self.vault.path.stem+'-before-import-'+__import__('uuid').uuid4().hex+'.sqlite');self.vault.backup(safety)
            for record in records:self.vault.save(record)
            self.refresh();self.auto_sync()
        except Exception as error:self.warning(error)
    def change_password(self):
        current,ok=self.password_prompt()
        if not ok:return
        new=self.new_password('Change account password')
        if new is not None:
            try:self.vault.change_password(current,new);self.auto_sync()
            except Exception as error:self.warning(error)
    def key_request(self,operation):
        from app import Window
        return Window.key_request(self,operation)
    def unlock_key(self):
        pin,ok=QInputDialog.getText(self,'YubiKey','FIDO2 PIN:',QLineEdit.EchoMode.Password)
        if not ok:return
        try:
            from yubikey_auth import unlock
            settings=self.vault.yubikey_settings(self.username.text())
            if not settings:raise VaultError('No YubiKey enrolled for this account.')
            response=self.key_request(lambda event:unlock(settings,pin,event));self.vault.unlock_yubikey(settings,response)
            self.master.clear();self.touch();self.history.remember(self.vault.path);self.update_state();self.refresh();self.complete_lookup();self.auto_sync()
        except Exception as error:self.warning(error)
    def enroll(self):
        password,ok=self.password_prompt()
        if not ok:return
        try:
            self.vault.verify_password(password)
            pin,ok=QInputDialog.getText(self,'Enroll YubiKey','FIDO2 PIN:',QLineEdit.EchoMode.Password)
            if not ok:return
            from yubikey_auth import enroll
            credential,salt,response=self.key_request(lambda event:enroll(pin,event));self.vault.enroll_yubikey(credential,salt,response);self.update_state();self.auto_sync()
        except Exception as error:self.warning(error)
    def lock_settings(self):
        minutes,ok=QInputDialog.getInt(self,'Lock Settings','Minutes of inactivity (0 = Unlimited):',self.lock_minutes,0,10080)
        if ok:
            if minutes==0 and QMessageBox.warning(self,'Unlimited','The vault will remain unlocked until you lock or close it. Continue?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            save_timeout(minutes);self.lock_minutes=minutes;self.lock_timer.stop();self.touch()
    def sync_settings(self):
        if self.task:return
        config=read_settings(self.vault);dialog=QDialog(self);dialog.setWindowTitle('Shared-folder Sync');form=QFormLayout(dialog)
        folder=QLineEdit(config.get('folder',''));choose=QPushButton('Choose shared folder…')
        def select_folder():
            path=QFileDialog.getExistingDirectory(dialog,'Shared folder',folder.text())
            if path:folder.setText(path)
        choose.clicked.connect(select_folder);form.addRow('Folder:',folder);form.addRow(choose)
        limit=QSpinBox();limit.setRange(1,1000);limit.setValue(config.get('limit',10));form.addRow('Maximum automatic backups:',limit)
        automatic=QCheckBox('Automatic sync, including while locked');automatic.setChecked(config.get('automatic',True));form.addRow(automatic)
        interval=QSpinBox();interval.setRange(5,86400);interval.setValue(config.get('interval',30));form.addRow('Interval (seconds):',interval)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);form.addRow(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        self.dialog=dialog
        try:
            if dialog.exec()==QDialog.DialogCode.Accepted:
                configure(self.vault,folder.text(),limit.value(),automatic.isChecked(),interval.value());self.auto_timer.start(self.interval());self.conflicted=False
        except Exception as error:self.warning(error)
        finally:self.dialog=None;dialog.deleteLater();self.auto_sync()
    def auto_sync(self):
        config=read_settings(self.vault)
        if not config.get('folder') or not config.get('automatic',True) or not self.vault.path.exists() or self.conflicted:return False
        if self.task or self.dialog:self.again=True;return False
        self.start_sync(False);return True
    def sync_now(self):
        if self.task:return
        if self.conflicted and self.vault.unlocked:self.resolve();return
        self.start_sync(True)
    def start_sync(self,manual,choices=None,expected=None):
        if self.task:return
        self.manual=manual;self.again=False;self.close_display();session=self.vault.session()
        self.task=SyncTask(self.vault.path,session,choices,expected);self.task.finished.connect(self.sync_finished)
        self.sync_status.setText('Syncing…');self.update_state();self.task.start()
    def sync_finished(self):
        task=self.task;self.task=None
        self.conflicted=task.conflict
        if task.error:self.sync_status.setText('Sync stopped: '+task.error)
        else:
            try:
                session=self.vault.session()
                if session:self.vault.resume(session)
                self.refresh();self.sync_status.setText(task.result);self.complete_lookup()
            except Exception as error:self.lock();self.sync_status.setText(str(error))
        task.deleteLater();self.update_state()
        if self.manual and task.error:
            if task.conflict and self.vault.unlocked:QTimer.singleShot(0,self.resolve)
            else:self.warning(task.error)
        if self.closing:
            if task.error:self.warning('Local data is saved, but final sync failed: '+task.error)
            self.closing=False;self.lock();self.close_ready=True;self.close();return
        if self.again and not self.conflicted:QTimer.singleShot(0,self.auto_sync)
    def resolve(self):
        config=read_settings(self.vault)
        if not config.get('folder') or not self.vault.unlocked:return
        temporary=tempfile.TemporaryDirectory(prefix='wormwright-managed-compare-')
        other=ManagedVault(Path(temporary.name)/'shared.sqlite')
        try:
            shutil.copyfile(Path(config['folder'])/'wormwright-vault.sqlite',other.path)
            other.resume(self.vault.session());ours=state(self.vault.path);theirs=state(other.path)
            defaults=combined(config.get('managed_baseline'),ours,theirs)
            if defaults is None:
                self.resolve_management(other,ours,theirs);return
            local={r['id']:r for r in self.vault.entries(self.vault.manager)};shared={r['id']:r for r in other.entries(other.manager)}
            unresolved=[eid for eid,value in defaults.items() if value is None]
            if any(eid not in local or eid not in shared for eid in unresolved) and not self.vault.manager:
                raise VaultError('A conflict involves unavailable or deleted entries. Ask the Manager to resolve it.')
            dialog=QDialog(self);dialog.setWindowTitle('Resolve Entry Differences');dialog.resize(1000,450);layout=QVBoxLayout(dialog)
            layout.addWidget(QLabel('Passwords stay masked. Double-clicking is disabled. Choose local or shared for each competing entry; independent changes are retained.'))
            table=QTableWidget(len(unresolved),4);table.setHorizontalHeaderLabels(['Local description / notes','Shared description / notes','Deleted status','Use']);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);layout.addWidget(table)
            selectors=[]
            for i,eid in enumerate(unresolved):
                a=local.get(eid,{});b=shared.get(eid,{})
                table.setItem(i,0,QTableWidgetItem(a.get('description','Absent')+'\n'+a.get('notes','')));table.setItem(i,1,QTableWidgetItem(b.get('description','Absent')+'\n'+b.get('notes','')))
                table.setItem(i,2,QTableWidgetItem(f'Local: {a.get("deleted",False)} / Shared: {b.get("deleted",False)}'))
                selector=QComboBox();selector.addItems(['Choose…','Local','Shared']);table.setCellWidget(i,3,selector);selectors.append(selector)
            buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons);apply=buttons.button(QDialogButtonBox.StandardButton.Apply);apply.setEnabled(not unresolved)
            for selector in selectors:selector.currentIndexChanged.connect(lambda:apply.setEnabled(all(s.currentIndex()>0 for s in selectors)))
            apply.clicked.connect(dialog.accept);buttons.rejected.connect(dialog.reject);self.dialog=dialog
            if dialog.exec()==QDialog.DialogCode.Accepted:
                choices=dict(defaults)
                for eid,selector in zip(unresolved,selectors):choices[eid]='local' if selector.currentIndex()==1 else 'shared'
                self.conflicted=False;self.start_sync(True,choices,[ours,theirs])
            self.dialog=None;dialog.deleteLater()
        except Exception as error:self.warning(error)
        finally:other.lock();temporary.cleanup()
    def resolve_management(self,other,ours,theirs):
        if not self.vault.manager or not other.manager:
            raise VaultError('Only the Manager can resolve account/group conflicts. Both copies are retained.')
        dialog=QDialog(self);dialog.setWindowTitle('Manager — Reconcile Access and Entries');dialog.resize(1000,520);layout=QVBoxLayout(dialog)
        warning=QLabel('Choose one complete set of accounts, memberships, exclusions and credentials. This determines who receives the resulting entries. Both originals are backed up. Entry groups missing from those settings require explicit reassignment.');warning.setWordWrap(True);layout.addWidget(warning)
        authority=QComboBox();authority.addItems(['Choose access settings…','Local access settings','Shared access settings']);layout.addWidget(authority)
        a={r['id']:r for r in self.vault.entries(True)};b={r['id']:r for r in other.entries(True)};ids=sorted(set(a)|set(b))
        table=QTableWidget(len(ids),3);table.setHorizontalHeaderLabels(['Local entry','Shared entry','Keep']);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);layout.addWidget(table);selectors=[]
        for i,eid in enumerate(ids):
            left=a.get(eid);right=b.get(eid)
            for column,record in enumerate((left,right)):
                table.setItem(i,column,QTableWidgetItem((record['description']+(' [Deleted]' if record.get('deleted') else '')) if record else '(Permanently absent)'))
            choose=QComboBox();choose.addItems(['Choose…','Local','Shared'])
            fields=('description','link','user_name','password','notes','creator','groups','deleted')
            if left and right and all(left.get(k)==right.get(k) for k in fields):choose.setCurrentIndex(1)
            elif left is None:choose.setCurrentIndex(2)
            elif right is None:choose.setCurrentIndex(1)
            table.setCellWidget(i,2,choose);selectors.append(choose)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons);apply=buttons.button(QDialogButtonBox.StandardButton.Apply)
        def enable():apply.setEnabled(authority.currentIndex()>0 and all(s.currentIndex()>0 for s in selectors))
        authority.currentIndexChanged.connect(enable)
        for selector in selectors:selector.currentIndexChanged.connect(enable)
        enable();apply.clicked.connect(dialog.accept);buttons.rejected.connect(dialog.reject);self.dialog=dialog
        try:
            if dialog.exec()!=QDialog.DialogCode.Accepted:return
            target=self.vault if authority.currentIndex()==1 else other;labels=target.available_groups();assignments={};choices={}
            for eid,selector in zip(ids,selectors):
                side='local' if selector.currentIndex()==1 else 'shared';choices[eid]=side;record=(a if side=='local' else b).get(eid)
                if record and any(g not in labels for g in record['groups']):
                    d=QDialog(dialog);d.setWindowTitle('Assign groups — '+record['description']);l=QVBoxLayout(d);l.addWidget(QLabel('Its original groups are missing. Explicitly choose the groups that will receive this entry.'))
                    groups=groups_list(labels,[]);l.addWidget(groups);btn=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);l.addWidget(btn);btn.accepted.connect(d.accept);btn.rejected.connect(d.reject)
                    if d.exec()!=QDialog.DialogCode.Accepted:d.deleteLater();return
                    assignments[eid]=selected_groups(groups);d.deleteLater()
            password,ok=self.password_prompt()
            if not ok:return
            self.vault.verify_password(password)
            message=reconcile(self.vault.path,self.vault.session(),'local' if authority.currentIndex()==1 else 'shared',choices,[ours,theirs],assignments)
            self.vault.resume(self.vault.session());self.conflicted=False;self.refresh();self.sync_status.setText(message)
        finally:self.dialog=None;dialog.deleteLater()

    def closeEvent(self,event):
        if not getattr(self,'close_ready',False):
            if self.task:
                self.closing=True;event.ignore();return
            if self.auto_sync():self.closing=True;event.ignore();return
        self.auto_timer.stop();self.lock();event.accept()
