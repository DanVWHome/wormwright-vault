"""An extra view of one controller/session, with no database or sync worker."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView

class CompanionView(QMainWindow):
    def __init__(self,controller,manager):
        super().__init__(controller)
        self.controller=controller;self.manager=manager
        self.setWindowTitle('Wormwright Vault Manager' if manager else 'Wormwright Vault')
        self.setWindowIcon(controller.windowIcon());self.resize(1100,650)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        self.status=QLabel();layout.addWidget(self.status)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search description, link or notes');row.addWidget(self.search)
        self.search.textChanged.connect(controller.search.setText);self.buttons=[]
        for text,callback in [('Add',controller.add),('Edit',controller.edit),('Delete',controller.delete),('Lock',controller.lock)]:
            b=QPushButton(text);b.clicked.connect(callback);row.addWidget(b);self.buttons.append(b)
            if text=='Delete':self.delete_button=b
        layout.addLayout(row)
        help_menu=self.menuBar().addMenu('Help');help_menu.addAction('Searchable Help…',controller.show_help);help_menu.addSeparator();help_menu.addAction('About Wormwright Vault…',controller.show_about)
        self.management=[]
        if manager:
            menu=self.menuBar().addMenu('Manage')
            for text,callback in [('Users & Groups…',controller.manage),('Individual Exclusions…',controller.exclusions),('Restore Selected Entry',controller.restore_entry),('Permanently Delete Selected Entry…',controller.purge),('Emergency Lockdown…',controller.emergency_lockdown)]:
                a=menu.addAction(text);a.triggered.connect(callback);self.management.append(a)
            a=menu.addAction('Show deleted entries');a.setCheckable(True);a.toggled.connect(controller.show_deleted.setChecked);self.deleted_action=a
            a=menu.addAction('Only deleted entries');a.setCheckable(True);a.toggled.connect(controller.only_deleted.setChecked);self.only_deleted_action=a
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['Description','Link','User Name','Password'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.currentCellChanged.connect(self.select);self.table.cellDoubleClicked.connect(controller.edit);layout.addWidget(self.table)
        layout.addWidget(QLabel('Shares the main session. Both views lock together. Close this view to keep the main window open.'))
        self.refresh()
    def select(self,row,*args):
        if row>=0:self.controller.table.selectRow(row)
    def refresh(self):
        c=self.controller;unlocked=c.vault.unlocked
        self.status.setText(('Unlocked' if unlocked else 'Locked — unlock in the main window')+' • '+str(c.vault.path))
        self.search.blockSignals(True);self.search.setText(c.search.text());self.search.blockSignals(False);self.search.setEnabled(unlocked and (not self.manager or c.vault.manager))
        for b in self.buttons:b.setEnabled(unlocked and (not self.manager or c.vault.manager) and not c.task and not c.dialog)
        self.delete_button.setText(c.delete_button.text())
        self.delete_button.setEnabled(self.delete_button.isEnabled() and c.selected() is not None)
        for a in self.management:a.setEnabled(c.vault.manager and not c.task and not c.dialog)
        if self.manager:
            self.deleted_action.blockSignals(True);self.deleted_action.setChecked(c.show_deleted.isChecked());self.deleted_action.blockSignals(False);self.deleted_action.setEnabled(c.vault.manager and not c.task)
        if self.manager:
            self.only_deleted_action.blockSignals(True);self.only_deleted_action.setChecked(c.only_deleted.isChecked());self.only_deleted_action.blockSignals(False);self.only_deleted_action.setEnabled(c.vault.manager and not c.task)
        self.table.blockSignals(True);self.table.setRowCount(0)
        if unlocked and (not self.manager or c.vault.manager):
            for i,r in enumerate(c.records):
                self.table.insertRow(i)
                for j,key in enumerate(['description','link','user_name']):
                    item=QTableWidgetItem(r.get(key,'')+(' [Deleted]' if j==0 and r.get('deleted') else ''))
                    if r.get('deleted'):item.setBackground(QColor('#ffe0e0'));item.setForeground(QColor('#7c1515'))
                    self.table.setItem(i,j,item)
                box=QWidget()
                if r.get('deleted'):box.setStyleSheet('QWidget { background-color: #ffe0e0; color: #7c1515; }')
                row=QHBoxLayout(box);row.setContentsMargins(2,0,2,0);row.addWidget(QLabel('••••••••'))
                for text,callback in [('Show',lambda checked=False,r=r:c.reveal(r)),('Copy',lambda checked=False,r=r:c.copy_text(r['password']))]:
                    b=QPushButton(text);b.setEnabled(not c.task and not c.dialog);b.clicked.connect(callback);row.addWidget(b)
                self.table.setCellWidget(i,3,box)
        self.table.blockSignals(False)
    def closeEvent(self,event):
        self.hide();event.ignore()
