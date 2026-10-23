"""Options for "Remove background": quality and what goes behind the subject."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QDialogButtonBox, QFrame)

import background_engine as be
from i18n import tr

STYLE = """
QDialog { background:#0B1A2E; color:#EAF4FF; }
QLabel { color:#DCEBFC; background:transparent; }
QLabel#title { font-size:19px; font-weight:800; color:#FFFFFF; }
QLabel#hint { color:#93B2D3; font-size:12px; }
QComboBox { background:#152C49; border:1px solid #31597F; border-radius:8px; padding:6px 10px; color:#EAF4FF; }
QFrame#card { background:#112440; border:1px solid #284A70; border-radius:12px; }
QPushButton { color:#EAF4FF; background:#1A3555; border:1px solid #31597F; border-radius:9px; padding:9px 16px; font-weight:600; }
QPushButton:hover { background:#24496F; }
"""


class BackgroundDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.settings = QSettings('Morphix', 'Morphix')
        self.setWindowTitle(tr('Morphix · Remove background'))
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLE)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        title = QLabel(tr('Remove the background'))
        title.setObjectName('title')
        lay.addWidget(title)
        info = QLabel(tr('{n} image(s). The subject keeps its exact original pixels and full resolution; '
                         'only the background is removed.', n=len(paths)))
        info.setObjectName('hint')
        info.setWordWrap(True)
        lay.addWidget(info)

        card = QFrame()
        card.setObjectName('card')
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Quality')))
        self.quality = QComboBox()
        for key, (_f, size, label, *_rest) in be.MODELS.items():
            usable = be.quality_allowed(key)
            mark = '  ✓' if be.model_path(key) else ''
            self.quality.addItem(f'{tr(label)}  ·  {size}{mark}', key)
            if not usable:
                self.quality.model().item(self.quality.count() - 1).setEnabled(False)
        idx = self.quality.findData(self.settings.value('bg/quality', 'standard'))
        if idx >= 0 and be.quality_allowed(self.quality.itemData(idx)):
            self.quality.setCurrentIndex(idx)
        row.addWidget(self.quality, 1)
        form.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Background')))
        self.background = QComboBox()
        for key, label in (('transparent', 'Transparent (PNG)'), ('white', 'White'), ('black', 'Black')):
            self.background.addItem(tr(label), key)
        idx = self.background.findData(self.settings.value('bg/background', 'transparent'))
        self.background.setCurrentIndex(max(0, idx))
        row.addWidget(self.background, 1)
        form.addLayout(row)
        lay.addWidget(card)

        note = QLabel(tr('Works fully offline. The first time, the model is downloaded once (internet needed). '
                         '“Finest edges” is best for hair and fur and needs 16 GB of memory.'))
        note.setObjectName('hint')
        note.setWordWrap(True)
        lay.addWidget(note)
        buttons = QDialogButtonBox()
        ok = buttons.addButton(tr('Remove background'), QDialogButtonBox.AcceptRole)
        ok.setStyleSheet('background:#247FE4; border-color:#55A3FB; color:white;')
        buttons.addButton(tr('Cancel'), QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def options(self):
        self.settings.setValue('bg/quality', self.quality.currentData())
        self.settings.setValue('bg/background', self.background.currentData())
        return {'bg_quality': self.quality.currentData(), 'background': self.background.currentData()}


def ask_background_options(paths, parent=None):
    dialog = BackgroundDialog(paths, parent)
    dialog.setWindowFlag(Qt.WindowStaysOnTopHint, parent is None)
    if dialog.exec() != QDialog.Accepted:
        return None
    return dialog.options()
