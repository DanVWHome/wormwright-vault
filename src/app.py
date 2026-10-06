import os
import sys
import threading
from collections import Counter
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtCore import Qt, QTimer, QThread, QEventLoop, QEvent
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QTextEdit, QDialogButtonBox, QFileDialog,
    QListWidget, QListWidgetItem, QCheckBox, QProgressDialog, QInputDialog, QSpinBox)
from vault import Vault, VaultError
from importer import read_export
from exporter import export_csv
from hooks import default_vault, send, LocalControl
from search import matching_ids
from history import VaultHistory
from sync import configure, read_settings, synchronize, DEFAULT_LIMIT, SyncConflict
from conflicts import Comparison
from conflict_dialog import ConflictDialog
from preferences import read_timeout, save_timeout


class KeyTask(QThread):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.cancelled = threading.Event()
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.operation(self.cancelled)
        except Exception as error:
            self.error = str(error)
        finally:
            self.operation = None


class ImportPreview(QDialog):
    def __init__(self, parent, records):
        super().__init__(parent)
        self.records = records
        self.setWindowTitle('Preview Vault Import')
        self.resize(900, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'{len(records)} entries • Exact duplicates will be skipped • A safety backup is saved before import'))
        self.table = QTableWidget(len(records), 5)
        self.table.setHorizontalHeaderLabels(['Description', 'Link', 'User Name', 'Password', 'Notes'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for index, record in enumerate(records):
            for column, field in enumerate(['description', 'link', 'user_name', 'password', 'notes']):
                self.table.setItem(index, column, QTableWidgetItem('••••••••' if field == 'password' else record[field]))
        layout.addWidget(self.table)
        reveal = QCheckBox('Show passwords for verification')
        reveal.toggled.connect(self.show_passwords)
        layout.addWidget(reveal)
        verified = QCheckBox('I checked the entries and verified that the passwords are correct')
        layout.addWidget(verified)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Import Entries')
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        verified.toggled.connect(buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def show_passwords(self, checked):
        for index, record in enumerate(self.records):
            self.table.item(index, 3).setText(record['password'] if checked else '••••••••')

    def clear_secrets(self):
        self.table.setRowCount(0)
        self.records.clear()


class EntryDialog(QDialog):
    def __init__(self, parent, record=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Password' if record else 'Add Password')
        self.resize(560, 400)
        self.record = dict(record or {})
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.fields = {}
        for key, label in [('description', 'Description'), ('link', 'Link'), ('user_name', 'User Name'), ('password', 'Password')]:
            field = QLineEdit(self.record.get(key, ''))
            self.fields[key] = field
            if key == 'password':
                field.setEchoMode(QLineEdit.EchoMode.Password)
                row = QHBoxLayout()
                row.addWidget(field)
                show = QPushButton('Show')
                show.setCheckable(True)
                show.toggled.connect(lambda checked: (field.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password), show.setText('Hide' if checked else 'Show')))
                row.addWidget(show)
                form.addRow(label, row)
            else:
                form.addRow(label, field)
        self.notes = QTextEdit(self.record.get('notes', ''))
        form.addRow('Notes', self.notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate(self):
        if not self.fields['description'].text().strip():
            QMessageBox.warning(self, 'Description needed', 'Enter a description for this password.')
            return
        self.accept()

    def value(self):
        return {**self.record, **{key: field.text() for key, field in self.fields.items()}, 'notes': self.notes.toPlainText()}


class PasswordDisplay(QDialog):
    """Non-modal, large plain-text display cleared when closed or locked."""
    def __init__(self, parent, record):
        super().__init__(parent)
        self.setWindowTitle('Password — ' + record['description'])
        self.resize(800, 260)
        layout = QVBoxLayout(self)
        self.password_text = QTextEdit()
        self.password_text.setReadOnly(True)
        font = QFont('monospace', 32)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.password_text.setFont(font)
        self.password_text.setPlainText(record['password'])
        layout.addWidget(self.password_text)
        close = QPushButton('Close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def done(self, result):
        self.password_text.clear()
        super().done(result)

    def closeEvent(self, event):
        self.password_text.clear()
        super().closeEvent(event)


class Window(QMainWindow):
    def __init__(self, path):
        super().__init__()
        self.vault = Vault(path)
        self.vault_history = VaultHistory()
        self.lock_minutes = read_timeout()
        self.records = []
        self.dialog = None
        self.password_display = None
        self.clipboard_value = None
        self.password_fallback = False
        self.key_task = None
        self.pending_lookup = None
        self.setWindowTitle('Wormwright Vault — Offline Prototype')
        asset = Path(__file__).resolve().parent.parent / 'assets/wormwright-vault.png'
        if getattr(sys, 'frozen', False):
            asset = Path(sys._MEIPASS) / 'assets/wormwright-vault.png'
        self.setWindowIcon(QIcon(str(asset)))
        self.resize(1100, 640)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        title = QLabel('Wormwright Vault')
        title.setStyleSheet('font-size: 26px; font-weight: bold;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QHBoxLayout()
        brand.addStretch()
        mascot = QLabel()
        mascot.setPixmap(QPixmap(str(asset)).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand.addWidget(mascot)
        brand.addWidget(title)
        brand.addStretch()
        layout.addLayout(brand)
        self.status = QLabel()
        layout.addWidget(self.status)
        unlock = QHBoxLayout()
        self.master = QLineEdit()
        self.master.setPlaceholderText('Master password')
        self.master.setEchoMode(QLineEdit.EchoMode.Password)
        self.master.returnPressed.connect(self.unlock)
        unlock.addWidget(self.master)
        self.unlock_button = QPushButton('Unlock / Create Vault')
        self.unlock_button.clicked.connect(self.unlock)
        unlock.addWidget(self.unlock_button)
        self.key_unlock_button = QPushButton('Unlock with YubiKey — PIN + Touch')
        self.key_unlock_button.clicked.connect(self.unlock_key)
        unlock.addWidget(self.key_unlock_button)
        self.fallback_button = QPushButton('Use Fallback Password')
        self.fallback_button.clicked.connect(self.show_fallback)
        unlock.addWidget(self.fallback_button)
        choose = QPushButton('Choose Vault…')
        choose.clicked.connect(self.choose)
        unlock.addWidget(choose)
        recent = QPushButton('Recent Vaults…')
        recent.clicked.connect(self.recent_vaults)
        unlock.addWidget(recent)
        layout.addLayout(unlock)
        actions = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search description, link, or notes')
        self.search.textChanged.connect(self.refresh)
        actions.addWidget(self.search)
        self.controls = []
        for text, method in [('Add Password', self.add), ('Edit', self.edit), ('Clone', self.clone), ('Copy Password', self.copy), ('Delete', self.delete), ('Lock', self.lock)]:
            button = QPushButton(text)
            button.clicked.connect(method)
            actions.addWidget(button)
            self.controls.append(button)
        layout.addLayout(actions)
        backups = QHBoxLayout()
        backups.addStretch()
        for text, method in [('Import Vault CSV…', self.import_csv), ('Export to CSV…', self.export_csv), ('Back Up Vault…', self.backup), ('Restore Backup…', self.restore), ('Sync Settings…', self.sync_settings), ('Sync Now', self.sync_now)]:
            button = QPushButton(text)
            button.clicked.connect(method)
            backups.addWidget(button)
            self.controls.append(button)
        layout.addLayout(backups)
        authentication = QHBoxLayout()
        authentication.addStretch()
        for text, method in [('Set Up YubiKey…', self.enroll_key), ('Change Fallback Password…', self.change_fallback)]:
            button = QPushButton(text)
            button.clicked.connect(method)
            authentication.addWidget(button)
            self.controls.append(button)
        layout.addLayout(authentication)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Count', 'Description', 'Link', 'User Name', 'Password', 'Duplicate Password'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet('QTableWidget { alternate-background-color: #c9eaf5; background-color: white; color: #202020; } QHeaderView::section { background: silver; color: black; padding: 6px; }')
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        layout.addWidget(self.table)
        timeout_button = QPushButton('Lock Settings…')
        timeout_button.clicked.connect(self.lock_settings)
        layout.addWidget(timeout_button)
        self.lock_status = QLabel()
        layout.addWidget(self.lock_status)
        self.lock_timer = QTimer(self)
        self.lock_timer.setSingleShot(True)
        self.lock_timer.timeout.connect(self.lock)
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.timeout.connect(self.clear_clipboard)
        QApplication.instance().installEventFilter(self)
        self.restart_lock_timer()
        self.update_state()

    def restart_lock_timer(self):
        self.lock_timer.stop()
        label = f'Auto-lock after {self.lock_minutes} minutes of inactivity' if self.lock_minutes else 'Auto-lock: Unlimited — remember to lock manually'
        self.lock_status.setText('Clipboard clears after 30 seconds • ' + label)
        if self.vault.unlocked and self.lock_minutes:
            self.lock_timer.start(self.lock_minutes * 60 * 1000)

    def eventFilter(self, watched, event):
        if hasattr(self, 'lock_timer') and self.vault.unlocked and event.type() in (
                QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
            self.restart_lock_timer()
        return super().eventFilter(watched, event)

    def lock_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Automatic vault locking')
        form = QFormLayout(dialog)
        minutes = QSpinBox()
        minutes.setRange(0, 10080)
        minutes.setSpecialValueText('Unlimited')
        minutes.setValue(self.lock_minutes)
        form.addRow('Minutes of inactivity (0 = Unlimited):', minutes)
        warning = QLabel('Unlimited leaves passwords accessible until you lock or close the app. Use it only on a trusted device and remember to lock manually.')
        warning.setWordWrap(True)
        form.addRow(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            if minutes.value() == 0 and QMessageBox.warning(self, 'Disable automatic locking?',
                    warning.text(), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            save_timeout(minutes.value())
            self.lock_minutes = minutes.value()
            self.restart_lock_timer()
        except Exception as error:
            QMessageBox.warning(self, 'Lock settings not saved', str(error))
        finally:
            dialog.deleteLater()

    def update_state(self):
        unlocked = self.vault.unlocked
        self.status.setText(f"{'Unlocked' if unlocked else 'Locked'} • {self.vault.path}")
        try:
            has_key = self.vault.yubikey_settings() is not None
        except Exception:
            has_key = False
        password_visible = not unlocked and (not has_key or self.password_fallback)
        self.master.setVisible(password_visible)
        self.master.setPlaceholderText('Fallback vault password' if has_key else 'Master password')
        self.unlock_button.setVisible(password_visible)
        self.key_unlock_button.setVisible(not unlocked and has_key)
        self.fallback_button.setVisible(not unlocked and has_key and not self.password_fallback)
        self.search.setEnabled(unlocked)
        for button in self.controls:
            button.setEnabled(unlocked)

    def show_fallback(self):
        self.password_fallback = True
        self.update_state()
        self.master.setFocus()

    def handle_control(self, request):
        if request['action'] == 'lock':
            self.lock()
        else:
            if self.dialog:
                self.dialog.reject()
                if hasattr(self.dialog, "clear_secrets"):
                    self.dialog.clear_secrets()
                else:
                    for field in self.dialog.fields.values():
                        field.clear()
                    self.dialog.notes.clear()
                    self.dialog.record.clear()
            if request['action'] == 'lookup':
                self.pending_lookup = request['query']
            if self.vault.unlocked:
                self.refresh()  # Re-mask any passwords previously revealed by hand.
                self.complete_pending_lookup()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def complete_pending_lookup(self):
        if not self.vault.unlocked or self.pending_lookup is None:
            return
        query = self.pending_lookup
        self.pending_lookup = None
        self.search.setText(query)
        self.refresh()
        selected = 0
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text().casefold() == query.casefold():
                selected = row
                break
        if self.table.rowCount():
            self.table.selectRow(selected)
            self.table.scrollToItem(self.table.item(selected, 1))

    def key_request(self, operation):
        task = KeyTask(operation)
        self.key_task = task
        progress = QProgressDialog('Touch your YubiKey when it flashes.\nEnrollment may request two touches.', 'Cancel', 0, 0, self)
        progress.setWindowTitle('YubiKey PIN + Touch')
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.canceled.connect(task.cancelled.set)
        task.finished.connect(progress.accept)
        task.start()
        progress.exec()
        if task.isRunning():
            task.cancelled.set()
            loop = QEventLoop()
            task.finished.connect(loop.quit)
            if task.isRunning():
                loop.exec()
        self.key_task = None
        result, error = task.result, task.error
        task.result = None
        task.deleteLater()
        progress.deleteLater()
        if task.cancelled.is_set():
            raise VaultError('YubiKey operation cancelled. Your fallback password still works.')
        if error:
            raise VaultError(error)
        return result

    def unlock_key(self):
        pin, ok = QInputDialog.getText(self, 'YubiKey unlock', 'YubiKey FIDO2 PIN:', QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            if not pin:
                raise VaultError('Enter your YubiKey PIN.')
            from yubikey_auth import unlock
            settings = self.vault.yubikey_settings()
            if settings is None:
                raise VaultError('No YubiKey is enrolled for this vault.')
            response = self.key_request(lambda event: unlock(settings, pin, event))
            self.vault.unlock_yubikey(settings, response)
            response = None
            self.remember_vault()
            self.restart_lock_timer()
            self.update_state()
            self.refresh()
            self.complete_pending_lookup()
        except Exception as error:
            self.lock()
            QMessageBox.warning(self, 'YubiKey unlock failed', str(error))
        finally:
            pin = None

    def enroll_key(self):
        password, ok = QInputDialog.getText(self, 'Authorize YubiKey enrollment', 'Current fallback/master password:', QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            self.vault.verify_password(password)
            password = None
            if self.vault.yubikey_settings() is not None:
                answer = QMessageBox.question(self, 'Replace enrolled key?', 'This replaces the key enrolled for this vault. The fallback password will continue to work. Continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
            pin, ok = QInputDialog.getText(self, 'Set up YubiKey', 'Existing YubiKey FIDO2 PIN:', QLineEdit.EchoMode.Password)
            if not ok:
                return
            if not pin:
                raise VaultError('Enter your YubiKey PIN.')
            from yubikey_auth import enroll
            credential, salt, response = self.key_request(lambda event: enroll(pin, event))
            pin = None
            safety = self.vault.enroll_yubikey(credential, salt, response)
            response = None
            self.update_state()
            QMessageBox.information(self, 'YubiKey enrolled', 'Your YubiKey is now the primary unlock option. Try PIN + touch.\n\nYour existing vault password remains the fallback.\nSafety backup:\n' + str(safety))
        except Exception as error:
            QMessageBox.warning(self, 'YubiKey not enrolled', str(error))
        finally:
            password = None
            pin = None

    def change_fallback(self):
        form = QDialog(self)
        form.setWindowTitle('Change fallback vault password')
        layout = QFormLayout(form)
        fields = []
        for label in ['Current vault password', 'New fallback password', 'Confirm new password']:
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addRow(label, field)
            fields.append(field)
        layout.addRow(QLabel('You may choose the same password as Linux login/sudo.\nWormwright AI does not authenticate against Linux or update that password.\nA changed password may be any non-empty length. Old backups retain their old password.'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(form.accept)
        buttons.rejected.connect(form.reject)
        layout.addRow(buttons)
        try:
            if form.exec() != QDialog.DialogCode.Accepted:
                return
            if fields[1].text() != fields[2].text():
                raise VaultError('New passwords do not match.')
            safety = self.vault.change_password(fields[0].text(), fields[1].text())
            self.update_state()
            QMessageBox.information(self, 'Fallback password changed', 'The new fallback password is ready. YubiKey enrollment is preserved.\n\nThe safety backup still uses the previous password:\n' + str(safety))
        except Exception as error:
            QMessageBox.warning(self, 'Password not changed', str(error))
        finally:
            for field in fields:
                field.clear()
            form.deleteLater()

    def unlock(self):
        password = self.master.text()
        self.master.clear()
        try:
            if self.vault.path.exists():
                self.vault.unlock(password)
            else:
                password, ok = self.password_creation()
                if not ok:
                    return
                self.vault.create(password)
                for description, link, username, secret in [('Demo Mail', 'https://mail.example.com', 'demo@example.com', 'Demo-only-password!'), ('Demo Router', 'https://router.example.com', 'admin', 'Another-demo-password!'), ('Demo Account', 'https://account.example.com', 'demo', 'Demo-only-password!')]:
                    self.vault.save({'description': description, 'link': link, 'user_name': username, 'password': secret, 'notes': 'Dummy entry. No real credentials.'})
            self.remember_vault()
            self.restart_lock_timer()
            self.update_state()
            self.refresh()
            self.complete_pending_lookup()
        except Exception as error:
            self.vault.lock()
            self.update_state()
            QMessageBox.warning(self, 'Cannot unlock vault', str(error))

    def password_creation(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Create encrypted vault')
        form = QFormLayout(dialog)
        password = QLineEdit()
        password.setObjectName('new_master_password')
        password.setEchoMode(QLineEdit.EchoMode.Password)
        confirmation = QLineEdit()
        confirmation.setObjectName('confirm_master_password')
        confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('New master password (12+ characters):', password)
        form.addRow('Confirm master password:', confirmation)
        error = QLabel()
        error.setWordWrap(True)
        form.addRow(error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        def accept():
            if len(password.text()) < 12:
                error.setText('Use a master password of at least 12 characters.')
            elif password.text() != confirmation.text():
                error.setText('Master passwords do not match. Enter the same password in both fields.')
            else:
                dialog.accept()
        buttons.accepted.connect(accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        password.setFocus()
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return '', False
            return password.text(), True
        finally:
            password.clear()
            confirmation.clear()
            dialog.deleteLater()

    def remember_vault(self):
        try:
            self.vault_history.remember(self.vault.path)
        except OSError:
            QMessageBox.warning(self, 'History not saved', 'The vault is unlocked, but its location could not be added to recent history.')

    def recent_vaults(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Recent Vaults')
        dialog.resize(760, 340)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Remembered locations on this device. Removing a location does not delete its vault.'))
        locations = QListWidget()
        def populate():
            locations.clear()
            for path in self.vault_history.read():
                item = QListWidgetItem(path + ('' if Path(path).is_file() else ' — unavailable'))
                item.setData(Qt.ItemDataRole.UserRole, path)
                locations.addItem(item)
        populate()
        layout.addWidget(locations)
        buttons = QHBoxLayout()
        open_button = QPushButton('Open selected')
        forget_button = QPushButton('Forget selected')
        close_button = QPushButton('Close')
        for button in (open_button, forget_button, close_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        def open_selected():
            item = locations.currentItem()
            if item is None:
                return
            path = item.data(Qt.ItemDataRole.UserRole)
            if not Path(path).is_file():
                QMessageBox.warning(dialog, 'Vault unavailable', 'This vault is missing or its drive is not mounted. Its location stays in history.\n\n' + path)
                return
            if Path(path).resolve() == self.vault.path.resolve():
                dialog.accept()
                return
            self.lock()
            self.vault = Vault(path)
            self.update_state()
            dialog.accept()
        def forget_selected():
            item = locations.currentItem()
            if item is not None:
                try:
                    self.vault_history.forget(item.data(Qt.ItemDataRole.UserRole))
                    populate()
                except OSError as error:
                    QMessageBox.warning(dialog, 'History not updated', str(error))
        open_button.clicked.connect(open_selected)
        locations.itemDoubleClicked.connect(lambda *_: open_selected())
        forget_button.clicked.connect(forget_selected)
        close_button.clicked.connect(dialog.reject)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def choose(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open Wormwright AI vault', str(self.vault.path.parent), 'SQLite vault (*.sqlite);;All files (*)')
        if filename and Path(filename).resolve() != self.vault.path.resolve():
            self.lock()
            self.vault = Vault(filename)
            self.update_state()

    def sync_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Shared-folder sync')
        form = QFormLayout(dialog)
        settings = read_settings(self.vault)
        folder = QLineEdit(settings.get('folder', ''))
        browse = QPushButton('Choose shared folder…')
        def choose_folder():
            selected = QFileDialog.getExistingDirectory(dialog, 'Choose mounted shared folder', folder.text())
            if selected:
                folder.setText(selected)
        browse.clicked.connect(choose_folder)
        form.addRow('Mounted folder:', folder)
        form.addRow(browse)
        limit = QSpinBox()
        limit.setRange(1, 1000)
        limit.setValue(settings.get('limit', DEFAULT_LIMIT))
        form.addRow('Maximum automatic sync backups per copy:', limit)
        note = QLabel('Use a dedicated folder for this vault. Each device keeps a local copy.\nSync runs only when you click Sync Now. Conflicting edits are never overwritten.\nOnly automatic sync backups are pruned after successful sync; manual backups are kept.\nUse a mounted network share, not a folder mirrored by another sync program.')
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                configure(self.vault, folder.text(), limit.value())
            except Exception as error:
                QMessageBox.warning(self, 'Sync settings', str(error))

    def sync_now(self):
        try:
            result = synchronize(self.vault)
            if not self.vault.unlocked:
                self.lock()
            self.update_state()
            self.refresh()
            QMessageBox.information(self, 'Sync complete', result)
        except SyncConflict:
            self.resolve_sync_conflict()
        except Exception as error:
            if not self.vault.unlocked:
                self.lock()
            self.update_state()
            QMessageBox.warning(self, 'Sync stopped', str(error))

    def resolve_sync_conflict(self):
        comparison = None
        try:
            comparison = Comparison(self.vault)
            password, ok = QInputDialog.getText(self, 'Unlock shared vault for comparison',
                'Enter the shared vault’s master / fallback password:', QLineEdit.EchoMode.Password)
            if not ok or not self.vault.unlocked:
                return
            comparison.unlock_shared(password)
            password = ''
            self.dialog = ConflictDialog(self, comparison)
            if self.dialog.exec() != QDialog.DialogCode.Accepted or not self.vault.unlocked:
                return
            choices = self.dialog.choices()
            answer = QMessageBox.question(self, 'Apply resolved entries?',
                'Write your selected entries to both vault copies? Encrypted safety backups of both originals will be kept. '
                'The local vault will then use the shared vault’s password and YubiKey settings.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            safety = comparison.apply(choices)
            self.update_state()
            self.refresh()
            QMessageBox.information(self, 'Differences resolved',
                'Both copies now contain your selected entries. Your vault remains open; future unlocks use the shared vault’s credentials.\n\nSafety backups:\n' + '\n'.join(map(str, safety)))
        except Exception as error:
            QMessageBox.warning(self, 'Resolution stopped', str(error))
        finally:
            if self.dialog:
                self.dialog.clear_secrets()
                self.dialog.deleteLater()
                self.dialog = None
            if comparison:
                comparison.close()
            if not self.vault.unlocked:
                self.lock()
            self.update_state()

    def backup(self):
        from datetime import datetime
        suggested = self.vault.path.with_name('vanwormai-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.sqlite')
        filename, _ = QFileDialog.getSaveFileName(self, 'Save encrypted backup (choose a new filename)', str(suggested), 'SQLite vault (*.sqlite)')
        if not filename:
            return
        try:
            self.vault.backup(filename)
            QMessageBox.information(self, 'Backup saved', 'Encrypted backup saved to:\n' + filename + '\n\nKeep the master password used by this backup.')
        except Exception as error:
            QMessageBox.warning(self, 'Backup not saved', str(error))

    def authorize_export(self):
        settings = self.vault.yubikey_settings()
        method = 'Fallback password'
        if settings is not None:
            method, ok = QInputDialog.getItem(self, 'Authenticate CSV export',
                'Authenticate again for this export:', ['YubiKey PIN + Touch', 'Fallback password'], 0, False)
            if not ok:
                return None
        if method == 'YubiKey PIN + Touch':
            pin, ok = QInputDialog.getText(self, 'Authorize CSV export', 'YubiKey FIDO2 PIN:', QLineEdit.EchoMode.Password)
            if not ok:
                return None
            try:
                if not pin:
                    raise VaultError('Enter your YubiKey PIN.')
                from yubikey_auth import unlock
                response = self.key_request(lambda event: unlock(settings, pin, event))
                return {'yubikey_settings': settings, 'yubikey_response': response}
            finally:
                pin = None
        password, ok = QInputDialog.getText(self, 'Authorize CSV export', 'Current fallback/master password:', QLineEdit.EchoMode.Password)
        return {'password': password} if ok else None

    def export_csv(self):
        answer = QMessageBox.question(self, 'Export readable passwords?',
            'CSV exports contain all entries and their passwords in readable plain text.\n'
            'Anyone who can read the file can see them. This is not an encrypted backup.\n\n'
            'Export all entries, including those outside the current search?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        from datetime import datetime
        suggested = self.vault.path.parent / ('wormwright-export-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.csv')
        filename, _ = QFileDialog.getSaveFileName(self, 'Export Vault CSV (choose a new filename)', str(suggested), 'CSV export (*.csv)')
        if not filename:
            return
        if not filename.lower().endswith('.csv'):
            filename += '.csv'
        try:
            authorization = self.authorize_export()
            if authorization is None:
                return
            try:
                export_csv(self.vault, filename, **authorization)
            finally:
                authorization.clear()
            QMessageBox.information(self, 'CSV exported', 'Plain-text CSV saved to:\n' + filename + '\n\nKeep this file private. Use Back Up Vault for encrypted backups.')
        except Exception as error:
            QMessageBox.warning(self, 'CSV not exported', str(error))

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose Vault CSV export', str(self.vault.path.parent), 'CSV export (*.csv)')
        if not filename:
            return
        records = []
        try:
            records = read_export(filename)
            if not self.vault.unlocked:
                raise VaultError('The vault locked while choosing the CSV. Unlock it and try again.')
            self.dialog = ImportPreview(self, records)
            if self.dialog.exec() == QDialog.DialogCode.Accepted and self.vault.unlocked:
                imported, skipped, safety = self.vault.import_records(records)
                self.refresh()
                message = f'Imported {imported} entries. Skipped {skipped} exact duplicates.'
                if safety:
                    message += '\n\nYour previous vault was saved to:\n' + str(safety)
                QMessageBox.information(self, 'Import complete', message)
        except Exception as error:
            QMessageBox.warning(self, 'Import not completed', str(error))
        finally:
            if self.dialog:
                self.dialog.clear_secrets()
                self.dialog.deleteLater()
                self.dialog = None
            records.clear()

    def restore(self):
        from PySide6.QtWidgets import QInputDialog
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose encrypted backup to restore', str(self.vault.path.parent), 'SQLite vault (*.sqlite);;All files (*)')
        if not filename:
            return
        answer = QMessageBox.question(self, 'Replace current vault?', 'Restore replaces all current entries with the backup. It does not merge them.\n\nA safety backup of your current vault will be saved first. Continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        password, ok = QInputDialog.getText(self, 'Unlock backup', 'Master password for the backup:', QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            safety = self.vault.restore(filename, password)
            self.update_state()
            self.refresh()
            QMessageBox.information(self, 'Backup restored', 'Restore complete. The vault remains open. Future unlocks use the backup’s master password.\n\nYour previous vault was saved to:\n' + str(safety))
        except Exception as error:
            if not self.vault.unlocked:
                self.lock()
            QMessageBox.warning(self, 'Restore not completed', str(error))

    def refresh(self):
        self.close_password_display()
        if not self.vault.unlocked:
            return
        try:
            self.records = self.vault.entries()
        except Exception:
            self.lock()
            QMessageBox.warning(self, 'Vault error', 'An encrypted entry could not be read. The vault has been locked.')
            return
        counts = Counter(record['password'] for record in self.records if record['password'])
        matched = matching_ids(self.records, self.search.text())
        visible = [record for record in self.records if record['id'] in matched]
        self.table.setRowCount(len(visible))
        for row, record in enumerate(visible):
            values = [str(row + 1), record['description'], record['link'], record['user_name'], '', f"Used in {counts[record['password']]} entries" if counts[record['password']] > 1 else '']
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record['id'])
                self.table.setItem(row, column, item)
            password_cell = QWidget()
            password_layout = QHBoxLayout(password_cell)
            password_layout.setContentsMargins(4, 0, 4, 0)
            password_label = QLineEdit('••••••••')
            password_label.setReadOnly(True)
            password_label.setFrame(False)
            password_label.setMinimumWidth(0)
            password_label.setStyleSheet('color: #202020; background: transparent; border: none;')
            password_layout.addWidget(password_label, 1)
            reveal = QPushButton('Show')
            reveal.setFixedWidth(54)
            reveal.clicked.connect(lambda checked=False, entry_id=record['id']: self.show_password(entry_id))
            password_layout.addWidget(reveal)
            self.table.setCellWidget(row, 4, password_cell)
        self.table.resizeRowsToContents()

    def close_password_display(self):
        if self.password_display is not None:
            self.password_display.reject()
            self.password_display.deleteLater()
            self.password_display = None

    def show_password(self, entry_id):
        self.close_password_display()
        record = next((record for record in self.records if record['id'] == entry_id), None)
        if not self.vault.unlocked or record is None:
            return
        self.password_display = PasswordDisplay(self, record)
        self.password_display.show()
        self.password_display.raise_()
        self.password_display.activateWindow()

    def selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'Select an entry', 'Select a password entry first.')
            return None
        entry_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((record for record in self.records if record['id'] == entry_id), None)

    def save_dialog(self, record=None):
        self.dialog = EntryDialog(self, record)
        try:
            if self.dialog.exec() == QDialog.DialogCode.Accepted and self.vault.unlocked:
                self.vault.save(self.dialog.value())
                self.refresh()
        except Exception as error:
            QMessageBox.warning(self, 'Cannot save', str(error))
        finally:
            self.dialog.deleteLater()
            self.dialog = None

    def add(self):
        self.save_dialog()

    def edit(self):
        record = self.selected()
        if record:
            self.save_dialog(record)

    def clone(self):
        record = self.selected()
        if record:
            record = dict(record)
            record.pop('id')
            record['description'] += ' (copy)'
            self.save_dialog(record)

    def copy(self):
        record = self.selected()
        if record:
            self.clipboard_value = record['password']
            QApplication.clipboard().setText(self.clipboard_value)
            self.clipboard_timer.start(30000)

    def clear_clipboard(self):
        if self.clipboard_value is not None and QApplication.clipboard().text() == self.clipboard_value:
            QApplication.clipboard().clear()
        self.clipboard_value = None

    def delete(self):
        record = self.selected()
        if record and QMessageBox.question(self, 'Delete password', f"Delete {record['description']}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes and self.vault.unlocked:
            self.vault.delete(record['id'])
            self.refresh()

    def lock(self):
        self.close_password_display()
        self.lock_timer.stop()
        self.pending_lookup = None
        self.password_fallback = False
        if self.key_task:
            self.key_task.cancelled.set()
        self.clear_clipboard()
        if self.dialog:
            self.dialog.reject()
            if hasattr(self.dialog, "clear_secrets"):
                self.dialog.clear_secrets()
            else:
                for field in self.dialog.fields.values():
                    field.clear()
                self.dialog.notes.clear()
                self.dialog.record.clear()
        self.vault.lock()
        self.records.clear()
        self.table.setRowCount(0)
        self.search.clear()
        self.master.clear()
        self.update_state()

    def closeEvent(self, event):
        self.lock()
        event.accept()


def main():
    import argparse
    os.umask(0o077)
    parser = argparse.ArgumentParser(description='Wormwright Vault')
    parser.add_argument('vault', nargs='?', type=Path, default=default_vault())
    parser.add_argument('--lookup')
    parser.add_argument('--check-yubikey-runtime', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_yubikey_runtime:
        from yubikey_auth import RP_ID, ORIGIN, DefaultClientDataCollector
        DefaultClientDataCollector(ORIGIN).verify_rp_id(RP_ID, ORIGIN)
        print('YubiKey runtime data loaded successfully.')
        return
    path = args.vault
    request = {'version': 1, 'action': 'lookup', 'query': args.lookup} if args.lookup is not None else {'version': 1, 'action': 'open'}
    try:
        send(path, request)
        return
    except (FileNotFoundError, ConnectionRefusedError):
        pass
    app = QApplication([sys.argv[0]])
    window = Window(path)
    try:
        control = LocalControl(path, window.handle_control)
    except Exception as error:
        QMessageBox.warning(window, 'Cannot open vault', str(error))
        return
    timer = QTimer(window)
    timer.timeout.connect(control.poll)
    timer.start(100)
    app.aboutToQuit.connect(control.close)
    window.show()
    window.handle_control(request)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
