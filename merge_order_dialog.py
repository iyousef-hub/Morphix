"""Explicit top-to-bottom ordering for multi-file PDF merges.

Finder and the Windows Explorer selection APIs do not reliably report the
chronological order of clicks. This dialog makes the final ordering explicit.
"""
from pathlib import Path
from PySide6.QtCore import Qt
from i18n import tr
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)


class MergeOrderDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Morphix · Merge order'))
        self.resize(560, 490)
        self.setMinimumWidth(425)
        root = QVBoxLayout(self)
        root.setSpacing(12)
        heading = QLabel(tr('Arrange the files in the final PDF'))
        heading.setStyleSheet('font-size: 18px; font-weight: 700;')
        root.addWidget(heading)
        hint = QLabel(tr('The top file comes first. Each PDF adds all of its pages and each image adds one page. '
                         'Finder does not always keep the order you clicked in, so please check the list.'))
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.files = QListWidget(self)
        self.files.setDragDropMode(QAbstractItemView.InternalMove)
        self.files.setDefaultDropAction(Qt.MoveAction)
        self.files.setSelectionMode(QAbstractItemView.SingleSelection)
        self.files.setAlternatingRowColors(True)
        for path in paths:
            path = str(path)
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            self.files.addItem(item)
        root.addWidget(self.files, 1)
        self.files.setCurrentRow(0)
        line = QHBoxLayout()
        up = QPushButton('↑ ' + tr('Move up'))
        down = QPushButton('↓ ' + tr('Move down'))
        up.clicked.connect(lambda: self.move_selected(-1))
        down.clicked.connect(lambda: self.move_selected(+1))
        line.addWidget(up)
        line.addWidget(down)
        line.addStretch()
        root.addLayout(line)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(tr('Merge in this order'))
        buttons.button(QDialogButtonBox.Cancel).setText(tr('Cancel'))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.setStyleSheet('''
          QDialog { background: #09182E; color: #EFF7FF; }
          QLabel { color: #DBE9FB; }
          QListWidget { background: #102640; color: #F5F9FF;
                        border: 1px solid #365F93; border-radius: 12px;
                        font-size: 13px; padding: 7px; }
          QListWidget::item { padding: 10px 6px; }
          QListWidget::item:selected { background: #2176C9; }
          QPushButton { background: #18365A; color: #EAF5FF;
                        border: 1px solid #3976B0; padding: 10px;
                        border-radius: 9px; }
          QPushButton:hover { background: #2467A7; }
        ''')

    def move_selected(self, direction):
        row = self.files.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.files.count():
            return
        item = self.files.takeItem(row)
        self.files.insertItem(target, item)
        self.files.setCurrentItem(item)

    def ordered_paths(self):
        return [self.files.item(i).data(Qt.UserRole) for i in range(self.files.count())]


def ask_merge_order(paths, parent=None):
    if len(paths) <= 1:
        return list(paths)
    dialog = MergeOrderDialog(paths, parent)
    return dialog.ordered_paths() if dialog.exec() == QDialog.Accepted else None
