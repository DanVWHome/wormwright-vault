"""Masked entry comparison. Secrets remain inside the vault application."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QTextEdit, QCheckBox, QDialogButtonBox

FIELDS = ('description', 'link', 'user_name', 'password', 'notes')

class ConflictDialog(QDialog):
    def __init__(self, parent, comparison):
        super().__init__(parent)
        self.comparison = comparison
        self.rows = comparison.compare()
        self.setWindowTitle('Resolve vault differences')
        self.resize(1050, 650)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Select a row to compare. Choose Local, Shared, or Omit for each entry.\nEntries missing from one side may be additions or deletions; review them explicitly.\nApplying writes the result to both copies, with encrypted safety backups. The shared vault’s unlock methods will be used.'))
        actions = QHBoxLayout()
        for label, choice in [('Use all local entries', 'local'), ('Use all shared entries', 'shared')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, c=choice: self.choose_all(c))
            actions.addWidget(button)
        layout.addLayout(actions)
        self.table = QTableWidget(len(self.rows), 4)
        self.table.setHorizontalHeaderLabels(['Local description', 'Shared description', 'Differences', 'Keep'])
        self.selectors = []
        for index, (_, local, shared) in enumerate(self.rows):
            differences = ', '.join(f for f in FIELDS if (local or {}).get(f, '') != (shared or {}).get(f, ''))
            status = 'Shared only' if local is None else 'Local only' if shared is None else differences or 'Identical'
            for col, text in enumerate([(local or {}).get('description', '—'), (shared or {}).get('description', '—'), status]):
                self.table.setItem(index, col, QTableWidgetItem(text))
            selector = QComboBox()
            selector.addItem('Choose…', None)
            selector.addItem('Local' if local else 'Local (absent: remove)', 'local')
            selector.addItem('Shared' if shared else 'Shared (absent: remove)', 'shared')
            selector.addItem('Omit entry', 'omit')
            if local == shared:
                selector.setCurrentIndex(1)
            selector.currentIndexChanged.connect(self.update_apply)
            self.table.setCellWidget(index, 3, selector)
            self.selectors.append(selector)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        details = QHBoxLayout()
        self.local_text = QTextEdit(); self.shared_text = QTextEdit()
        for title, widget in [('Local', self.local_text), ('Shared', self.shared_text)]:
            column = QVBoxLayout(); column.addWidget(QLabel(title)); widget.setReadOnly(True); column.addWidget(widget); details.addLayout(column)
        layout.addLayout(details)
        self.reveal = QCheckBox('Show passwords in this comparison')
        self.reveal.toggled.connect(self.show_details)
        layout.addWidget(self.reveal)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.table.currentCellChanged.connect(self.show_details)
        self.update_apply()
        if self.rows:
            self.table.setCurrentCell(0, 0)

    def update_apply(self, *args):
        if hasattr(self, 'buttons'):
            self.buttons.button(QDialogButtonBox.StandardButton.Apply).setEnabled(all(s.currentData() is not None for s in self.selectors))

    def choose_all(self, choice):
        for selector in self.selectors:
            selector.setCurrentIndex(selector.findData(choice))

    def choices(self):
        return [selector.currentData() for selector in self.selectors]

    def show_details(self, *args):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            return
        for record, widget in zip(self.rows[row][1:], (self.local_text, self.shared_text)):
            if record is None:
                widget.setPlainText('Entry absent from this copy.')
            else:
                widget.setPlainText('\n\n'.join(f'{field}: {"••••••••" if field == "password" and not self.reveal.isChecked() else record.get(field, "")}' for field in FIELDS))

    def clear_secrets(self):
        self.local_text.clear(); self.shared_text.clear()
        self.table.setRowCount(0)
        self.rows = []
