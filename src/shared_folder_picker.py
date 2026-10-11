"""Choose connected NAS shares using local paths the sync engine can access."""
import os
import sys
from pathlib import Path
from urllib.parse import unquote
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog, QDialogButtonBox)


def mounted_shares(runtime=None, home=None):
    """Discover already mounted SMB shares without connecting or reading files."""
    if sys.platform != 'linux':
        return []
    runtime = Path(runtime or os.environ.get('XDG_RUNTIME_DIR') or f'/run/user/{os.getuid()}')
    roots = [runtime / 'gvfs', Path(home or Path.home()) / '.gvfs']
    found = {}
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for path in entries:
            if not path.name.startswith('smb-share:'):
                continue
            fields = dict(part.split('=', 1) for part in path.name.split(':', 1)[1].split(',') if '=' in part)
            share = unquote(fields.get('share', 'Shared folder'))
            server = unquote(fields.get('server', 'NAS'))
            found[str(path)] = (f'{share} on {server}', path)
    return sorted(found.values(), key=lambda item: (item[0].casefold(), str(item[1])))


def _choose_location(parent, current='', file_mode=False):
    dialog = QDialog(parent)
    dialog.setWindowTitle('Open vault' if file_mode else 'Choose shared folder')
    dialog.resize(540, 340)
    layout = QVBoxLayout(dialog)
    help_text = QLabel('Select your connected NAS, or browse this computer, then choose a vault file.' if file_mode else 'Select your connected NAS, then choose a folder for this vault.')
    help_text.setWordWrap(True)
    layout.addWidget(help_text)
    shares = QListWidget()
    shares.setObjectName('connected_nas_shares')
    layout.addWidget(shares)
    status = QLabel()
    status.setWordWrap(True)
    layout.addWidget(status)
    actions = QHBoxLayout()
    refresh = QPushButton('Refresh')
    browse = QPushButton('Browse other folders…')
    actions.addWidget(refresh)
    actions.addWidget(browse)
    actions.addStretch()
    layout.addLayout(actions)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
    open_button = buttons.button(QDialogButtonBox.StandardButton.Open)
    open_button.setText('Choose vault…' if file_mode else 'Choose folder…')
    layout.addWidget(buttons)
    selection = {'path': None}

    def reload():
        old = shares.currentItem()
        previous = old.data(Qt.ItemDataRole.UserRole) if old else None
        shares.clear()
        mounts = mounted_shares()
        selected = 0
        for index, (label, path) in enumerate(mounts):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            shares.addItem(item)
            if str(path) == previous or (current and Path(current).is_relative_to(path)):
                selected = index
        status.setText('Connect your NAS in Files, then click Refresh.' if not mounts else '')
        if mounts:
            shares.setCurrentRow(selected)
        open_button.setEnabled(bool(mounts))

    def select():
        item = shares.currentItem()
        if item:
            selection['path'] = item.data(Qt.ItemDataRole.UserRole)
            dialog.accept()

    def other():
        selection['path'] = current or str(Path.home())
        dialog.accept()

    refresh.clicked.connect(reload)
    browse.clicked.connect(other)
    buttons.accepted.connect(select)
    buttons.rejected.connect(dialog.reject)
    shares.itemDoubleClicked.connect(lambda _: select())
    reload()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return ''
    # GNOME's native chooser can hide FUSE mounts or return remote URLs. The
    # Qt chooser navigates the accessible local mount and returns a local path.
    initial = selection['path']
    if current and Path(current).is_relative_to(initial):
        initial = current
    return initial


def choose_shared_folder(parent, current=''):
    if sys.platform != 'linux':
        return QFileDialog.getExistingDirectory(parent, 'Choose shared folder', current)
    initial = _choose_location(parent, current)
    if not initial:
        return ''
    return QFileDialog.getExistingDirectory(parent, 'Choose a dedicated shared folder', initial,
        QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog)


def choose_vault_file(parent, current=''):
    filters = 'SQLite vault (*.sqlite);;All files (*)'
    if sys.platform != 'linux':
        return QFileDialog.getOpenFileName(parent, 'Open vault', current, filters)[0]
    initial = _choose_location(parent, current, file_mode=True)
    if not initial:
        return ''
    return QFileDialog.getOpenFileName(parent, 'Open vault', initial, filters,
        options=QFileDialog.Option.DontUseNativeDialog)[0]
