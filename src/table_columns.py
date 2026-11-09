"""Device-local column widths; no vault contents are stored in preferences."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView
from platform_paths import data_home
from sync import atomic_json


def widths_path():
    return data_home() / 'vanwormai-vault/column-widths.json'


def read_settings():
    try:
        data = json.loads(widths_path().read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def configure_columns(table, profile, defaults):
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(60)
    header.setResizeContentsPrecision(250)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    widths = read_settings().get(profile)
    if not isinstance(widths, list) or len(widths) != len(defaults) or any(type(w) is not int or not 60 <= w <= 4096 for w in widths):
        widths = defaults
    for column, width in enumerate(widths):
        table.setColumnWidth(column, width)
        item = table.horizontalHeaderItem(column)
        hint = 'Drag the divider to resize; double-click it to fit the contents.'
        if item is not None:
            item.setToolTip((item.toolTip() + '\n' if item.toolTip() else '') + hint)
    def save_widths(*_):
        data = read_settings()
        data[profile] = [table.columnWidth(i) for i in range(table.columnCount())]
        try:
            path = widths_path()
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            atomic_json(path, data)
        except OSError:
            pass  # A preference failure must not prevent vault use.
    header.sectionResized.connect(save_widths)
    header.sectionHandleDoubleClicked.connect(table.resizeColumnToContents)
