"""Managed-format UI shared by Vault and the optional Vault Manager launcher."""
from website import add_website_action
from key_ui import request_key_pin
from pathlib import Path
import sys
import tempfile
import shutil
from collections import Counter
from PySide6.QtCore import Qt,QTimer,QThread,QEvent
from PySide6.QtGui import QIcon,QPixmap,QColor
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,
    QDialog,QDialogButtonBox,QFormLayout,QTextEdit,QMessageBox,QFileDialog,QCheckBox,QListWidget,
    QListWidgetItem,QInputDialog,QSpinBox,QMenu,QComboBox,QSplitter)
from managed_vault import ManagedVault,is_managed
from managed_sync import synchronize,state,combined,snapshot,reconcile
from vault import VaultError
from sync import read_settings,configure,SyncConflict
from preferences import read_timeout,save_timeout
from history import VaultHistory
from search import matching_ids
from exporter import export_csv
from importer import read_export
from version import VERSION, RELEASE_LABEL
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
        self.again=False;self.closing=False;self.conflicted=False;self.manual=False;self.companion=None
        self.lockdown_pending=False
        self.sort_column=0;self.sort_descending=False
        self.history=VaultHistory();self.lock_minutes=read_timeout();self.password_fallback=False
        self.setWindowTitle(f'Wormwright Vault{" Manager" if manager_app else ""} {VERSION} — {RELEASE_LABEL}')
        self.resize(1160,700)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        logo=QHBoxLayout();icon=QLabel();asset=Path(getattr(sys,'_MEIPASS',Path(__file__).parent.parent))/'assets'/('wormwright-vault-manager.png' if manager_app else 'wormwright-vault.png')
        if asset.exists():
            self.setWindowIcon(QIcon(str(asset)));icon.setPixmap(QPixmap(str(asset)).scaled(56,56,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));logo.addWidget(icon)
        title=QLabel('Wormwright Vault Manager' if manager_app else 'Wormwright Vault');title.setStyleSheet('font-size:26px;font-weight:bold')
        logo.addWidget(title);logo.addStretch();layout.addLayout(logo)
        layout.addWidget(QLabel(f'Version {VERSION} • {RELEASE_LABEL}'))
        self.status=QLabel();layout.addWidget(self.status)
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
        help_text=QLabel('Create a new vault to start from scratch. Open a local copy of an existing vault, or load the optional demo to learn. Local vaults can be saved anywhere on this computer; a separate folder is optional.');help_text.setWordWrap(True);welcome_layout.addWidget(help_text)
        welcome_row=QHBoxLayout()
        for text,callback in [('Create New Vault…',self.new_vault),('Open Existing Vault…',self.open_existing),('Load Demo Vault…',self.load_demo)]:
            b=QPushButton(text);b.clicked.connect(callback);welcome_row.addWidget(b)
        welcome_layout.addLayout(welcome_row);layout.addWidget(self.welcome)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search description, username, link or notes');self.search.textChanged.connect(self.refresh);row.addWidget(self.search)
        self.controls=[]
        for text,callback in [('Add',self.add),('Edit',self.edit),('Clone',self.clone),('Delete',self.delete),('Lock',self.lock)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button);self.controls.append(button)
            if text=='Delete':self.delete_button=button
        copy=QPushButton('Copy Field');menu=QMenu(copy)
        for field,label in [('description','Description'),('link','Link'),('user_name','User Name'),('password','Password'),('notes','Notes')]:
            menu.addAction(label,lambda checked=False,f=field:self.copy_field(f))
        copy.setMenu(menu);row.addWidget(copy);self.controls.append(copy);layout.addLayout(row)
        self.manager_row=QWidget();row=QHBoxLayout(self.manager_row);row.setContentsMargins(0,0,0,0)
        self.show_deleted=QCheckBox('Show deleted entries');self.show_deleted.setObjectName('show_deleted');self.show_deleted.toggled.connect(self.refresh);row.addWidget(self.show_deleted)
        self.only_deleted=QCheckBox('Only deleted entries');self.only_deleted.setObjectName('only_deleted');self.only_deleted.toggled.connect(self.refresh);row.addWidget(self.only_deleted);row.addStretch();layout.addWidget(self.manager_row)
        vault_menu=self.menuBar().addMenu('Vault')
        self.location_actions=[]
        for text,callback in [('Open Existing Vault…',self.open_existing),('Create New Vault…',self.new_vault),('Recent Vaults…',self.recent),('Choose Folder for New Vaults…',self.choose_folder)]:
            action=vault_menu.addAction(text);action.triggered.connect(callback);self.location_actions.append(action)
        vault_menu.addAction('Load Demo Vault…',self.load_demo)
        vault_menu.addSeparator();vault_menu.addAction('Vault Locations Explained…',self.location_help)
        data_menu=self.menuBar().addMenu('Import / Export / Backup')
        for text,callback in [('Import Vault CSV…',self.import_entries),('Export to CSV…',self.export),('Back Up Vault…',self.backup),('Restore Backup…',self.restore_backup)]:
            action=data_menu.addAction(text);action.triggered.connect(callback);self.controls.append(action)
        self.database_export_action=data_menu.addAction('Export Database…',self.export_database)
        self.management_menu=self.menuBar().addMenu('Manage');self.management_actions=[]
        for text,callback in [('Users & Groups…',self.manage),('Individual Exclusions…',self.exclusions),('Restore Selected Entry',self.restore_entry),('Permanently Delete Selected Entry…',self.purge),('Emergency Lockdown…',self.emergency_lockdown)]:
            action=self.management_menu.addAction(text);action.triggered.connect(callback);self.management_actions.append(action)
        view_menu=self.menuBar().addMenu('View');view_menu.addAction('Open Vault View',lambda:self.open_view(False));view_menu.addAction('Open Manager View',lambda:self.open_view(True))
        settings_menu=self.menuBar().addMenu('Settings');self.settings_actions=[]
        for text,callback in [('NAS Sync Settings…',self.sync_settings),('Sync Now',self.sync_now),('Lock Settings…',self.lock_settings)]:
            action=settings_menu.addAction(text);action.triggered.connect(callback);self.settings_actions.append(action)
        settings_menu.addSeparator()
        for text,callback in [('Set Up YubiKey…',self.enroll),('Change Account Password…',self.change_password)]:
            action=settings_menu.addAction(text);action.triggered.connect(callback);self.controls.append(action)
        help_menu=self.menuBar().addMenu('Help');help_menu.addAction('Searchable Help…',self.show_help);help_menu.addAction('Watch Tutorial…',self.show_tutorial);add_website_action(help_menu,self);help_menu.addSeparator();help_menu.addAction('About Wormwright Vault…',self.show_about)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['Description','Link','User Name','Password','Groups','Duplicate Password'])
        self.table.horizontalHeaderItem(3).setToolTip('Password sorting is disabled to protect password privacy.')
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);self.table.setColumnWidth(3,240)
        self.table.horizontalHeader().setSortIndicatorShown(True);self.table.horizontalHeader().setSortIndicator(0,Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_entries)
        self.table.cellDoubleClicked.connect(self.edit);self.table.currentCellChanged.connect(self.selection_changed);layout.addWidget(self.table)
        self.sync_status=QLabel('Sync not configured.');self.sync_status.setWordWrap(True);layout.addWidget(self.sync_status)
        clipboard_note=QLabel('Clipboard clears after 30 seconds • Deleted entries are visible only to the Manager');clipboard_note.setWordWrap(True);layout.addWidget(clipboard_note)
        self.clipboard_timer=QTimer(self);self.clipboard_timer.setSingleShot(True);self.clipboard_timer.timeout.connect(self.clear_clipboard)
        self.lock_timer=QTimer(self);self.lock_timer.setSingleShot(True);self.lock_timer.timeout.connect(self.lock)
        self.auto_timer=QTimer(self);self.auto_timer.timeout.connect(self.auto_sync);self.auto_timer.start(self.interval())
        QApplication.instance().installEventFilter(self)
        self.update_state();QTimer.singleShot(0,self.auto_sync)
        from window_geometry import fit_to_screen
        QTimer.singleShot(0, lambda: fit_to_screen(self, 1160, 700))

    def show_tutorial(self):
        from tutorial_window import show_tutorial
        show_tutorial(self)

    def show_about(self):
        from about_window import show_about
        show_about(self)

    def show_help(self):
        from help_window import show_help
        show_help(self)

    def load_demo(self):
        if self.task:return
        source=Path(getattr(sys,'_MEIPASS',Path(__file__).parent.parent))/'assets/demo/wormwright-demo.sqlite'
        path,_=QFileDialog.getSaveFileName(self,'Save a local demo copy',str(managed_locations.local_folder()/'wormwright-demo.sqlite'),'SQLite vault (*.sqlite)',options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:return
        target=Path(path)
        try:
            # Exclusive creation: never overwrite a real vault or a previous demo.
            with source.open('rb') as incoming,target.open('xb') as outgoing:
                target.chmod(0o600);shutil.copyfileobj(incoming,outgoing)
            self.open_path(target);self.username.setText('DemoManager')
            QMessageBox.information(self,'Demo vault ready','This is disposable test data.\nUsername: DemoManager\nPassword: DemoVault123!\n\nSee Help → Searchable Help → Learn with the demo vault for other accounts. The vault remains locked until you sign in.')
        except FileExistsError:self.warning('That file already exists. Choose a new filename to keep it safe.')
        except Exception as error:self.warning(error)

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
        missing=not self.vault.path.exists();self.welcome.setVisible(missing)
        self.status.setText(f'{"Unlocked" if unlocked else "Locked"} • Local vault: {self.vault.path}');self.status.setWordWrap(True)
        try:personal=self.vault.personal;has_key=self.vault.yubikey_settings(self.username.text()) is not None
        except Exception:personal=True;has_key=False
        self.username.setVisible(not unlocked and not personal)
        password_visible=not unlocked and (not has_key or self.password_fallback)
        self.master.setVisible(password_visible and not missing);self.unlock_button.setVisible(password_visible and not missing);self.unlock_button.setText('Unlock Vault')
        self.key_button.setVisible(not unlocked and has_key);self.fallback.setVisible(not unlocked and has_key and not self.password_fallback)
        self.manager_row.setVisible(self.vault.manager);self.search.setEnabled(unlocked)
        for button in self.controls:button.setEnabled(unlocked and not self.task)
        self.management_menu.menuAction().setVisible(self.vault.manager)
        for action in self.management_actions:action.setEnabled(unlocked and not self.task)
        for action in self.location_actions+self.settings_actions:action.setEnabled(not self.task)
        self.database_export_action.setEnabled(self.vault.manager and not self.task)
        self.show_deleted.setEnabled(unlocked and not self.task)
        self.only_deleted.setEnabled(self.vault.manager and not self.task)
        self.selection_changed()
        if self.companion:self.companion.refresh()

    def show_fallback(self):self.password_fallback=True;self.update_state()

    def password_prompt(self,label='Current account password:'):
        dialog=QInputDialog(self);dialog.setWindowTitle('Authenticate');dialog.setLabelText(label);dialog.setTextEchoMode(QLineEdit.EchoMode.Password);dialog.resize(560,160);dialog.setMinimumWidth(520)
        try:
            accepted=dialog.exec()==QDialog.DialogCode.Accepted
            return dialog.textValue(),accepted
        finally:dialog.setTextValue('');dialog.deleteLater()

    def reauthenticate(self):
        """Fresh current-account authentication, using enrolled hardware or fallback."""
        try:
            settings=self.vault.yubikey_settings()
            if settings:
                choice=QMessageBox(self);choice.setWindowTitle('Authenticate');choice.setText('Choose how to authenticate this action.')
                key=choice.addButton('YubiKey — PIN + Touch',QMessageBox.ButtonRole.AcceptRole)
                fallback=choice.addButton('Account Password',QMessageBox.ButtonRole.ActionRole)
                choice.addButton(QMessageBox.StandardButton.Cancel);choice.setDefaultButton(key);choice.exec()
                if choice.clickedButton()==key:
                    pin,ok=request_key_pin(self, 'YubiKey authentication', 'FIDO2 PIN:')
                    if not ok:return None
                    from yubikey_auth import unlock
                    response=self.key_request(lambda event:unlock(settings,pin,event))
                    self.vault.verify_yubikey(settings,response)
                    return {'yubikey_settings':settings,'yubikey_response':response}
                if choice.clickedButton()!=fallback:return None
            password,ok=self.password_prompt()
            if not ok:return None
            self.vault.verify_password(password)
            return {'password':password}
        except Exception as error:self.warning(error);return None

    def update_sort_indicators(self):
        order=Qt.SortOrder.DescendingOrder if self.sort_descending else Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(self.sort_column,order)
        if self.companion:
            header=self.companion.table.horizontalHeader()
            header.setSortIndicatorShown(self.sort_column in (0,1,2))
            if self.sort_column in (0,1,2):header.setSortIndicator(self.sort_column,order)

    def sort_entries(self,column):
        if column not in (0,1,2,4,5):
            self.update_sort_indicators()
            return
        self.sort_descending=not self.sort_descending if column==self.sort_column else False
        self.sort_column=column
        self.table.horizontalHeader().setSortIndicator(column,Qt.SortOrder.DescendingOrder if self.sort_descending else Qt.SortOrder.AscendingOrder)
        self.refresh()

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
        selected=self.selected();selected_id=selected["id"] if selected else None
        old_row=self.table.currentRow();vertical=self.table.verticalScrollBar().value();horizontal=self.table.horizontalScrollBar().value()
        if not self.vault.unlocked:return
        try:
            records=self.vault.entries(include_deleted=self.vault.manager and (self.show_deleted.isChecked() or self.only_deleted.isChecked()))
            if self.vault.manager and self.only_deleted.isChecked():records=[r for r in records if r.get('deleted')]
            ids=set(matching_ids(records,self.search.text())) if self.search.text() else {r['id'] for r in records}
            visible=[r for r in records if r['id'] in ids]
            groups=self.vault.available_groups()
            counts=Counter(r['password'] for r in records if r.get('password'))
            def sort_key(record):
                keys={0:'description',1:'link',2:'user_name'}
                if self.sort_column in keys:return str(record.get(keys[self.sort_column],'')).casefold()
                if self.sort_column not in (4,5):return str(record.get('description','')).casefold()
                if self.sort_column==4:return ', '.join(groups.get(g,'Shared group') for g in record['groups']).casefold()
                return counts[record.get('password','')]
            visible.sort(key=sort_key,reverse=self.sort_descending)
            if visible==self.records and groups==getattr(self,'rendered_groups',None) and counts==getattr(self,'rendered_counts',None):
                if self.companion:self.companion.refresh()
                return
            self.close_display();self.records=visible;self.rendered_groups=groups;self.rendered_counts=counts
            self.table.setUpdatesEnabled(False);self.table.blockSignals(True);self.table.setRowCount(0)
            self.table.setRowCount(len(self.records))
            for i,record in enumerate(self.records):
                values=[record['description']+(' [Deleted]' if record.get('deleted') else ''),record.get('link',''),record.get('user_name',''),'••••••••',
                    ', '.join(self.vault.available_groups().get(g,'Shared group') for g in record['groups']),
                    f'Used in {counts[record["password"]]} entries' if counts[record.get('password','')]>1 else '']
                for j,value in enumerate(values):
                    item=QTableWidgetItem(value)
                    if record.get('deleted'):
                        item.setBackground(QColor('#ffe0e0'));item.setForeground(QColor('#7c1515'));item.setToolTip('Deleted entry — select to restore')
                    self.table.setItem(i,j,item)
                widget=QWidget()
                if record.get('deleted'):widget.setStyleSheet('QWidget { background-color: #ffe0e0; color: #7c1515; }')
                row=QHBoxLayout(widget);row.setContentsMargins(2,0,2,0);row.addWidget(QLabel('••••••••'))
                for text,callback in [('Show',lambda checked=False,r=record:self.reveal(r)),('Copy',lambda checked=False,r=record:self.copy_text(r['password']))]:
                    button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
                self.table.setCellWidget(i,3,widget)
            if self.records:
                row=next((i for i,r in enumerate(self.records) if r['id']==selected_id),min(max(old_row,0),len(self.records)-1))
                self.table.selectRow(row)
            self.table.verticalScrollBar().setValue(vertical);self.table.horizontalScrollBar().setValue(horizontal)
            self.table.blockSignals(False);self.table.setUpdatesEnabled(True);self.selection_changed()
            if self.companion:self.companion.refresh()
        except Exception as error:self.lock();self.warning(error)
        finally:self.table.blockSignals(False);self.table.setUpdatesEnabled(True)

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
            dialog.notes.clear();dialog.record.clear();self.dialog=None;dialog.deleteLater();self.update_state()
            if self.again:QTimer.singleShot(0,self.auto_sync)

    def add(self):self.edit_record()
    def edit(self,*args):
        if self.selected():self.edit_record(self.selected())
    def clone(self):
        if self.selected():
            record={k:v for k,v in self.selected().items() if k in ('description','link','user_name','password','notes')}
            self.edit_record(record)
    def selection_changed(self,*args):
        record=self.selected()
        restoring=bool(record and record.get('deleted') and self.vault.manager)
        self.delete_button.setText('Restore' if restoring else 'Delete')
        self.delete_button.setEnabled(bool(record) and self.vault.unlocked and not self.task and not self.dialog)
        if self.companion:
            self.companion.delete_button.setText(self.delete_button.text())

    def delete(self):
        record=self.selected()
        if record and record.get('deleted') and self.vault.manager:
            if not self.task:self.restore_entry()
            return
        if record and not self.task and QMessageBox.question(self,'Hide entry','Mark this entry as deleted? The Manager can restore it.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            try:self.vault.delete(record['id']);self.refresh();self.auto_sync()
            except Exception as error:self.warning(error)
    def restore_entry(self):
        if self.selected() and self.vault.manager and not self.task:
            try:self.vault.restore_entry(self.selected()['id']);self.refresh();self.auto_sync()
            except Exception as error:self.warning(error)
    def purge(self):
        record=self.selected()
        if not record or not self.vault.manager or self.task:return
        if QMessageBox.question(self,'Permanently delete entry','Remove this record from the database permanently? Existing backups may retain it. This cannot be undone in the current vault.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        if not self.reauthenticate():return
        try:self.vault.purge(record['id']);self.refresh();self.auto_sync()
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
        if request['action'] in ('open_vault_view','open_manager_view'):
            self.open_view(request['action']=='open_manager_view');return
        if request['action']=='lock':self.lock()
        else:
            if request['action']=='lookup':self.pending_lookup=request['query']
            self.complete_lookup();self.showNormal();self.raise_();self.activateWindow()
    def complete_lookup(self):
        if self.vault.unlocked and self.pending_lookup is not None:
            query=self.pending_lookup;self.pending_lookup=None;self.search.setText(query);self.refresh()

    def open_view(self,manager):
        if manager==self.manager_app:
            self.showNormal();self.raise_();self.activateWindow();return
        if manager and self.vault.unlocked and not self.vault.manager:
            self.warning('Only the Manager can open the management view.');return
        if self.companion is None:
            from companion_view import CompanionView
            self.companion=CompanionView(self,manager)
        self.companion.refresh();self.companion.showNormal();self.companion.raise_();self.companion.activateWindow()

    def review_list(self,title,headers,rows,parent=None):
        dialog=QDialog(parent or self);dialog.setWindowTitle(title);dialog.resize(800,480);layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel(f'{len(rows)} items — passwords are never shown in this list.'))
        search=QLineEdit();search.setPlaceholderText('Search this list');layout.addWidget(search)
        table=QTableWidget(len(rows),len(headers));table.setHorizontalHeaderLabels(headers);table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(table)
        for i,values in enumerate(rows):
            for j,value in enumerate(values):table.setItem(i,j,QTableWidgetItem(str(value)))
        def filter_rows(query):
            for i,values in enumerate(rows):table.setRowHidden(i,query.casefold() not in ' '.join(map(str,values)).casefold())
        search.textChanged.connect(filter_rows);close=QPushButton('Close');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.exec();dialog.deleteLater()

    def location_help(self):
        QMessageBox.information(self,'Vault Locations',
            'Local vault: Save anywhere on this computer. A separate folder is optional.\n\n'
            'Folder for new vaults: '+str(managed_locations.local_folder())+'\n\n'
            'NAS sync: Choose a dedicated shared folder for this vault in Settings → NAS Sync Settings. '
            'Each computer keeps its own local working copy. Choosing a new local folder does not move the current vault.')

    def choose_folder(self):
        if self.task:return
        folder=QFileDialog.getExistingDirectory(self,'Choose local folder (dedicated folder optional)',str(managed_locations.local_folder()))
        if folder:
            managed_locations.remember(folder=folder);self.update_state()

    def new_vault(self):
        if self.task:return
        path,_=QFileDialog.getSaveFileName(self,'Save new local vault — any local folder',str(managed_locations.local_folder()/'vault.sqlite'),'SQLite vault (*.sqlite)',options=QFileDialog.Option.DontConfirmOverwrite)
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
            QMessageBox.information(self,'Unsupported vault','This file is not a supported current-format vault. Create a new vault or open a current-format copy.');return
        managed_locations.remember(vault=path)
        self.lock();self.lockdown_pending=False;self.vault=ManagedVault(path);self.username.clear();self.search.clear();self.password_fallback=False;self.update_state()
    def recent(self):
        dialog=QDialog(self);dialog.setWindowTitle('Recent Vaults');layout=QVBoxLayout(dialog);items=QListWidget();items.addItems(self.history.read());layout.addWidget(items)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Open|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()==QDialog.DialogCode.Accepted and items.currentItem() and not self.task:self.open_path(Path(items.currentItem().text()))
        dialog.deleteLater()
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
            records=[r for r in self.vault.entries() if uid in self.vault._recipients(r)]
            user_details.setText(f'{len(names)} groups • {len(records)} accessible entries\nIndividual exclusions can further restrict access.')
        def show_group():
            item=groups.currentItem()
            if not item:group_details.setText('Select a group to see its members and entry counts.');return
            gid=item.data(Qt.ItemDataRole.UserRole);admin=self.vault.administration();group=admin['groups'][gid]
            names=sorted(admin['users'][uid]['identity']['name']+(' [disabled]' if admin['users'][uid]['identity']['disabled'] else '') for uid in group['members'])
            records=[r for r in self.vault.entries(True) if gid in r['groups']]
            active=sum(not r.get('deleted',False) for r in records)
            group_details.setText(f'{len(names)} members\nEntries: {active} active, {len(records)-active} deleted.\nEntries may belong to multiple groups.')
        def populate():
            selected_uid=users.currentItem().data(Qt.ItemDataRole.UserRole) if users.currentItem() else None
            selected_gid=groups.currentItem().data(Qt.ItemDataRole.UserRole) if groups.currentItem() else None
            users.clear();groups.clear();admin=self.vault.administration()
            for uid,data in sorted(admin['users'].items(),key=lambda pair:pair[1]['identity']['name'].casefold()):
                identity=data['identity'];names=sorted(g['name'] for g in admin['groups'].values() if uid in g['members'])
                item=QListWidgetItem(identity['name']+f' — {len(names)} groups'+(' [disabled]' if identity['disabled'] else '')+(' [Manager]' if uid==self.vault.uid else ''))
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
                review=QDialog(form_dialog);review.setWindowTitle('Review sharing');review.resize(600,300);review_layout=QVBoxLayout(review)
                text=QLabel(f'This user will receive {len(records)} entries through their groups.\n\n'+('\n'.join(' '.join(r['description'].split())[:100] for r in records[:5]) or '(No current entries)')+('\n…' if len(records)>5 else ''));text.setWordWrap(True);review_layout.addWidget(text)
                full=QPushButton('View Full List…');full.clicked.connect(lambda:self.review_list('Entries to share',['Description','Link','User Name'],[[r.get(k,'') for k in ('description','link','user_name')] for r in records],review));review_layout.addWidget(full)
                buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Yes|QDialogButtonBox.StandardButton.Cancel);review_layout.addWidget(buttons);buttons.button(QDialogButtonBox.StandardButton.Yes).setText('Create Account');buttons.accepted.connect(review.accept);buttons.rejected.connect(review.reject)
                if review.exec()==QDialog.DialogCode.Accepted:self.vault.add_user(name.text(),password.text(),gids)
                review.deleteLater()
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
        def user_entries():
            uid=selected_user();records=[r for r in self.vault.entries() if uid in self.vault._recipients(r)]
            self.review_list('Accessible entries',['Description','Link','User Name'],[[r.get(k,'') for k in ('description','link','user_name')] for r in records],dialog)
        def user_groups():
            uid=selected_user();self.review_list('User groups',['Group'],[[g['name']] for g in self.vault.administration()['groups'].values() if uid in g['members']],dialog)
        def group_members():
            item=groups.currentItem()
            if not item:raise VaultError('Select a group.')
            admin=self.vault.administration();g=admin['groups'][item.data(Qt.ItemDataRole.UserRole)]
            self.review_list('Group members',['Member','Status'],[[admin['users'][uid]['identity']['name'],'Disabled' if admin['users'][uid]['identity']['disabled'] else 'Active'] for uid in g['members']],dialog)
        for text,callback in [('View Accessible Entries…',user_entries),('View User Groups…',user_groups)]:
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=callback:action(f));user_layout.addWidget(button)
        members=QPushButton('View Members…');members.clicked.connect(lambda:action(group_members));group_layout.addWidget(members)
        rename=QPushButton('Rename Manager…');rename.clicked.connect(lambda:action(rename_manager));user_layout.addWidget(rename)
        add=QPushButton('Add Group…');add.clicked.connect(lambda:action(add_group));group_layout.addWidget(add)
        close=QPushButton('Close');close.clicked.connect(dialog.accept);layout.addWidget(close)
        populate();self.dialog=dialog;dialog.exec();self.dialog=None;dialog.deleteLater();self.update_state();self.auto_sync()

    def exclusions(self):
        if not self.vault.manager or self.task:return
        admin=self.vault.administration();dialog=QDialog(self);dialog.setWindowTitle('Individual exclusions');layout=QVBoxLayout(dialog)
        users=QComboBox()
        for uid,data in admin['users'].items():
            if uid!=self.vault.uid:users.addItem(data['identity']['name'],uid)
        if not users.count():self.warning('Create an ordinary user first.');dialog.deleteLater();return
        layout.addWidget(QLabel('Checked entries are excluded, even through group membership or creation.'));layout.addWidget(users)
        search=QLineEdit();search.setObjectName('exclusion_search');search.setPlaceholderText('Search description, username, link or notes…');layout.addWidget(search)
        records=self.vault.entries(True);items=QListWidget();items.setObjectName('exclusion_entries');layout.addWidget(items)
        def filter_entries():
            ids=set(matching_ids(records,search.text())) if search.text() else {r['id'] for r in records}
            for i in range(items.count()):
                item=items.item(i);item.setHidden(item.data(Qt.ItemDataRole.UserRole) not in ids)
        search.textChanged.connect(filter_entries)
        def fill():
            items.clear();uid=users.currentData()
            for record in records:
                item=QListWidgetItem(record['description']+(' [Deleted]' if record.get('deleted') else ''));item.setData(Qt.ItemDataRole.UserRole,record['id']);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if any(r['entry']==record['id'] and r['user']==uid for r in admin['exclusions']) else Qt.CheckState.Unchecked);items.addItem(item)
            filter_entries()
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
        finally:self.dialog=None;dialog.deleteLater();self.update_state();self.auto_sync()

    def export_database(self):
        if not self.vault.manager or self.task:return
        if not self.reauthenticate():return
        try:
            path,_=QFileDialog.getSaveFileName(self,'Export encrypted database for another device',str(managed_locations.local_folder()/'vault-for-device.sqlite'),'SQLite vault (*.sqlite)',options=QFileDialog.Option.DontConfirmOverwrite)
            if not path:return
            overwrite=Path(path).exists()
            if overwrite and QMessageBox.question(self,'Replace exported database?',f'Replace the existing file?\n{path}\n\nThe existing copy will be replaced with this encrypted vault.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            self.vault.export_database(path,overwrite=overwrite)
            QMessageBox.information(self,'Encrypted database exported','This copy contains the whole encrypted vault. Each account can unlock only its permitted entries.\n\nOn the other computer choose Open Existing Vault, sign in, and configure the same shared sync folder. Sync this Manager copy before distributing it so it matches the shared master. Device settings and sync history are not included.')
        except Exception as error:self.warning(error)

    def emergency_lockdown(self):
        if not self.vault.manager or self.task:return
        if QMessageBox.warning(self,'Emergency Lockdown','Disable every ordinary account, including YubiKey access, while preserving the Manager? Connected devices are affected only after successfully downloading the update. Offline copies and previously copied passwords remain accessible. Re-enable users individually to recover.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        if not self.reauthenticate():return
        try:
            count=self.vault.emergency_lockdown()
            self.lockdown_pending=True;self.refresh();self.update_state()
            self.sync_status.setText(f'Lockdown saved locally: {count} ordinary accounts disabled. Shared publication pending.')
            if read_settings(self.vault).get('folder'):
                self.conflicted=False;self.start_sync(True)
            else:self.warning('Lockdown is saved locally. No shared folder is configured, so other devices have not received it. Configure NAS Sync Settings and sync to publish it.')
        except Exception as error:self.warning(error)

    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Back up encrypted vault','','SQLite vault (*.sqlite)')
        if path:
            try:self.vault.backup(path)
            except Exception as error:self.warning(error)
    def restore_backup(self):
        if not self.vault.manager or self.task:
            self.warning('Only the Manager may restore a whole-vault backup.');return
        if QMessageBox.warning(self,'Restore Backup','Restoring also restores old account credentials, memberships and exclusions. Previously revoked access may return. Save the current copy and continue?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        if not self.reauthenticate():return
        try:
            source,_=QFileDialog.getOpenFileName(self,'Choose encrypted backup','','SQLite vault (*.sqlite)')
            if not source:return
            username,ok=QInputDialog.getText(self,'Backup Manager','Manager username in the backup:',text='Manager')
            if not ok:return
            password,ok=self.password_prompt('Backup Manager password:')
            if not ok:return
            self.vault.restore(source,password,username);self.update_state();self.refresh();self.auto_sync()
        except Exception as error:self.warning(error)

    def export(self):
        if QMessageBox.warning(self,'Unencrypted CSV export','The exported file is not encrypted and includes passwords. Store it carefully and remove it when no longer needed. Continue?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        authentication=self.reauthenticate()
        if not authentication:return
        path,_=QFileDialog.getSaveFileName(self,'Export visible active entries to plaintext CSV','','CSV (*.csv)')
        if path:
            try:export_csv(self.vault,path,**authentication)
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
        authentication=self.reauthenticate()
        if not authentication:return
        new=self.new_password('Change account password')
        if new is not None:
            try:self.vault.change_password(authentication.get("password"),new,yubikey_settings=authentication.get("yubikey_settings"),yubikey_response=authentication.get("yubikey_response"));self.auto_sync()
            except Exception as error:self.warning(error)
    def key_request(self,operation):
        from app import Window
        return Window.key_request(self,operation)
    def unlock_key(self):
        pin,ok=request_key_pin(self, 'YubiKey', 'FIDO2 PIN:')
        if not ok:return
        try:
            from yubikey_auth import unlock
            settings=self.vault.yubikey_settings(self.username.text())
            if not settings:raise VaultError('No YubiKey enrolled for this account.')
            response=self.key_request(lambda event:unlock(settings,pin,event));self.vault.unlock_yubikey(settings,response)
            self.master.clear();self.touch();self.history.remember(self.vault.path);managed_locations.remember(vault=self.vault.path);self.update_state();self.refresh();self.complete_lookup();self.auto_sync()
        except Exception as error:self.warning(error)
    def enroll(self):
        if not self.reauthenticate():return
        try:
            pin,ok=request_key_pin(self, 'Enroll YubiKey', 'FIDO2 PIN:')
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
        config=read_settings(self.vault);dialog=QDialog(self);dialog.setWindowTitle('NAS Sync Settings');dialog.resize(600,380);form=QFormLayout(dialog)
        help_text=QLabel('Choose a dedicated shared NAS folder for this vault. This requirement applies only to the shared sync folder. Your local working vault can be saved in any local folder. Each computer keeps its own local copy.');help_text.setWordWrap(True);form.addRow(help_text)
        folder=QLineEdit(config.get('folder',''));choose=QPushButton('Choose shared folder…')
        def select_folder():
            path=QFileDialog.getExistingDirectory(dialog,'Shared folder',folder.text())
            if path:folder.setText(path)
        choose.clicked.connect(select_folder);form.addRow('Dedicated shared folder:',folder);form.addRow(choose)
        limit=QSpinBox();limit.setRange(1,1000);limit.setValue(config.get('limit',10));form.addRow('Maximum automatic backups:',limit)
        automatic=QCheckBox('Automatic sync, including while locked');automatic.setChecked(config.get('automatic',True));form.addRow(automatic)
        interval=QSpinBox();interval.setRange(5,86400);interval.setValue(config.get('interval',30));form.addRow('Interval (seconds):',interval)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);form.addRow(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        self.dialog=dialog
        try:
            if dialog.exec()==QDialog.DialogCode.Accepted:
                configure(self.vault,folder.text(),limit.value(),automatic.isChecked(),interval.value());self.auto_timer.start(self.interval());self.conflicted=False
        except Exception as error:self.warning(error)
        finally:self.dialog=None;dialog.deleteLater();self.update_state();self.auto_sync()
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
        self.manual=manual;self.again=False;session=self.vault.session()
        self.task=SyncTask(self.vault.path,session,choices,expected);self.task.finished.connect(self.sync_finished)
        self.sync_status.setText('Syncing…');self.update_state();self.task.start()
    def sync_finished(self):
        task=self.task;self.task=None
        self.conflicted=task.conflict
        if task.error:self.sync_status.setText(('Lockdown saved locally; shared publication pending. ' if self.lockdown_pending else '')+'Sync stopped: '+task.error)
        else:
            try:
                session=self.vault.session()
                if task.result!='Already up to date.':
                    if session:self.vault.resume(session)
                    self.refresh()
                self.sync_status.setText(task.result);self.complete_lookup()
                if self.lockdown_pending:
                    admin=self.vault.administration()
                    if all(data['identity']['disabled'] for uid,data in admin['users'].items() if uid!=self.vault.uid):
                        self.lockdown_pending=False;self.sync_status.setText('Lockdown synced to the shared master. Other devices are affected when they download it.')
                    else:self.sync_status.setText('Lockdown was not retained during reconciliation. Review user accounts immediately.')
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
            self.dialog=None;dialog.deleteLater();self.update_state()
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
            if not self.reauthenticate():return
            message=reconcile(self.vault.path,self.vault.session(),'local' if authority.currentIndex()==1 else 'shared',choices,[ours,theirs],assignments)
            self.vault.resume(self.vault.session());self.conflicted=False;self.refresh();self.sync_status.setText(message)
        finally:self.dialog=None;dialog.deleteLater();self.update_state()

    def closeEvent(self,event):
        if not getattr(self,'close_ready',False):
            if self.task:
                self.closing=True;event.ignore();return
            if self.auto_sync():self.closing=True;event.ignore();return
        self.auto_timer.stop();self.lock()
        if self.companion:self.companion.hide()
        event.accept()
