"""All tools for the selected files (Morphix 1.11).

Opened from “All tools” in the Action Hub. Shows every tool that works on the
current selection, grouped and searchable. Each tool has a pin (★): pinned tools
appear in the hub for this kind of selection, unpinned ones leave it — so the hub
is edited right here. “Always show all tools” makes every hub shape show the whole
list each time the shortcut is pressed.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QScrollArea,
                               QWidget, QFrame, QToolButton, QPushButton, QCheckBox)

from i18n import tr, option_row

SHOW_ALL_KEY = 'hub/show_all'

GROUPS = (
    ('Edit & organize', ('visual_pdf', 'visual_image', 'organize_pdf', 'rotate_pdf', 'crop_pdf', 'delete_pdf_pages',
                         'split_pdf', 'extract_pdf_pages', 'separate_pdf', 'image_rotate', 'image_crop',
                         'image_resize', 'image_grayscale', 'remove_bg', 'trim_media', 'scan_document')),
    ('Convert', ('pdf_word', 'pdf_png', 'pdf_png_zip', 'pdf_jpg_zip', 'images_pdf', 'image_png', 'image_jpg',
                 'image_webp', 'heic_jpg', 'office_pdf', 'docs_pdf_each', 'xlsx_pdf_fit', 'xlsx_csv', 'csv_xlsx',
                 'video_mp4', 'video_mp3', 'audio_mp3', 'ppt_media')),
    ('Merge & split', ('merge_pdf', 'merge_optimize', 'docs_merge_pdf', 'join_video', 'join_audio', 'xlsx_split',
                       'xlsx_merge')),
    ('Compress', ('optimize_pdf', 'image_compress', 'compress_media')),
    ('Text, speech & codes', ('extract_pdf_text', 'ocr_pdf_text', 'ocr_searchable_pdf', 'ocr_image_text',
                              'transcribe_media', 'read_qr')),
    ('Sign', ('sign_pdf', 'sign_images')),
    ('Archives', ('zip_files', 'tar_gz_files', 'rar_files')),
)


def group_of(key):
    for name, keys in GROUPS:
        if key in keys:
            return name
    return 'More'


def load_pins(settings, profile, defaults):
    try:
        config = json.loads(settings.value('wheel_v14/' + profile, 'null'))
    except (ValueError, TypeError):
        config = None
    return list(config) if isinstance(config, list) else list(defaults)


def save_pins(settings, profile, pins):
    settings.setValue('wheel_v14/' + profile, json.dumps(pins))


def toggle_pin(pins, key):
    """Pin → first in the hub (so it shows right away); unpin → removed. 'All tools' stays last."""
    pins = [k for k in pins if k != key] if key in pins else [key] + list(pins)
    if 'more_actions' in pins:
        pins = [k for k in pins if k != 'more_actions'] + ['more_actions']
    return pins


class ToolCard(QFrame):
    chosen = Signal(str)
    pin_toggled = Signal(str)

    def __init__(self, key, label, short, kind, pinned, accent):
        super().__init__()
        from hub_panel import action_icon
        self.key = key
        self.text = f'{label} {short}'.lower()
        self.setObjectName('toolCard')
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(label)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 6, 8)
        lay.setSpacing(9)
        icon = QLabel()
        icon.setPixmap(action_icon(kind, QColor(accent).lighter(150).name(), 26).pixmap(26, 26))
        icon.setFixedSize(28, 28)
        lay.addWidget(icon)
        name = QLabel(label)
        name.setWordWrap(True)
        name.setObjectName('toolName')
        lay.addWidget(name, 1)
        self.pin = QToolButton()
        self.pin.setObjectName('pin')
        self.pin.setCursor(Qt.PointingHandCursor)
        self.pin.clicked.connect(lambda: self.pin_toggled.emit(self.key))
        lay.addWidget(self.pin)
        self.set_pinned(pinned)

    def set_pinned(self, pinned):
        self.pin.setText('★' if pinned else '☆')
        self.pin.setProperty('on', bool(pinned))
        self.pin.setToolTip(tr('Remove from the hub') if pinned else tr('Pin to the hub'))
        self.pin.style().unpolish(self.pin)
        self.pin.style().polish(self.pin)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.chosen.emit(self.key)
        super().mouseReleaseEvent(event)


class ToolsLibrary(QDialog):
    """Pick a tool to run now, or pin / unpin tools for the hub."""
    def __init__(self, paths, profile, settings=None, accent='#3896FF', parent=None, hub_limit=6):
        super().__init__(parent)
        from main import supported_actions, ACTIONS
        from quickwheel import WHEEL_LABELS, PROFILES
        self.settings = settings or QSettings('Morphix', 'Morphix')
        self.profile = profile
        self.choice = None
        self.edit_requested = False
        self.keys = [k for k in supported_actions(paths) if k in ACTIONS]
        defaults = PROFILES.get(profile, ('', []))[1]
        self.pins = load_pins(self.settings, profile, defaults)
        self.setWindowTitle(tr('Morphix · All tools'))
        self.setModal(True)
        self.resize(640, 600)
        self.setStyleSheet(f'''
            QDialog {{ background: #0A1B31; color: #EBF5FF; }}
            QLabel {{ color: #DCEBFA; background: transparent; }}
            QLabel#big {{ font-size: 17px; font-weight: 750; color: #ACD9FF; }}
            QLabel#muted {{ color: #91B3D5; }}
            QLabel#group {{ color: #8EC5FF; font-weight: 700; font-size: 12px; padding-top: 6px; }}
            QLabel#toolName {{ color: #EAF4FF; font-size: 13px; }}
            QLineEdit {{ border: 1px solid #426D9E; border-radius: 10px; padding: 9px 12px; color: #EAF5FF;
                         background: #193351; font-size: 14px; }}
            QFrame#toolCard {{ background: #10263F; border: 1px solid #284B70; border-radius: 11px; }}
            QFrame#toolCard:hover {{ background: #173556; border-color: {accent}; }}
            QToolButton#pin {{ border: 0; background: transparent; color: #6F8FB0; font-size: 19px; padding: 2px 6px; }}
            QToolButton#pin[on="true"] {{ color: #FFD43B; }}
            QToolButton#pin:hover {{ color: #FFE58A; }}
            QPushButton {{ border: 1px solid #426D9E; border-radius: 9px; padding: 9px 14px; background: #17314E;
                           color: white; }}
            QScrollArea, QWidget#scrollBody {{ background: transparent; border: 0; }}
            QWidget#optionRow {{ background: transparent; }}
            QLabel#optionLabel {{ color: #DCEBFA; }}
        ''')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)
        title = QLabel(tr('All tools for these files'))
        title.setObjectName('big')
        lay.addWidget(title)
        from file_intelligence import file_summary
        sub = QLabel('  ·  '.join(file_summary(paths, max_lines=2)) + '  —  '
                     + tr('{n} tools', n=len(self.keys)))
        sub.setObjectName('muted')
        lay.addWidget(sub)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Search tools…'))
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)
        hint = QLabel(tr('Click a tool to run it. ★ pins it to the hub for this kind of file; '
                         'the hub shows the first {n} pinned tools.', n=hub_limit))
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        lay.addWidget(hint)

        body = QWidget()
        body.setObjectName('scrollBody')
        self.grid = QGridLayout(body)
        self.grid.setContentsMargins(0, 0, 4, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(7)
        self.cards, self.headers = [], []
        row = 0
        order = [g for g, _ in GROUPS] + ['More']
        for group in order:
            keys = [k for k in self.keys if group_of(k) == group]
            if not keys:
                continue
            header = QLabel(tr(group))
            header.setObjectName('group')
            self.grid.addWidget(header, row, 0, 1, 2)
            self.headers.append((header, keys))
            row += 1
            for i, key in enumerate(keys):
                short, kind = WHEEL_LABELS.get(key, (key, 'more'))
                card = ToolCard(key, tr(ACTIONS[key]), tr(short), kind, key in self.pins, accent)
                card.chosen.connect(self._choose)
                card.pin_toggled.connect(self._toggle)
                self.grid.addWidget(card, row + i // 2, i % 2)
                self.cards.append(card)
            row += (len(keys) + 1) // 2
        self.grid.setRowStretch(row, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)

        self.show_all = QCheckBox()
        self.show_all.setChecked(self.settings.value(SHOW_ALL_KEY, False, type=bool))
        self.show_all.toggled.connect(lambda on: self.settings.setValue(SHOW_ALL_KEY, bool(on)))
        lay.addWidget(option_row(self.show_all, tr('Always show all tools in the hub (every shape) '
                                                   'when I press the shortcut')))
        buttons = QHBoxLayout()
        edit = QPushButton(tr('Edit order in Settings…'))
        edit.clicked.connect(self._edit)
        close = QPushButton(tr('Close'))
        close.clicked.connect(self.reject)
        buttons.addWidget(edit)
        buttons.addStretch()
        buttons.addWidget(close)
        lay.addLayout(buttons)
        self.search.setFocus()

    def _filter(self, text):
        q = text.strip().lower()
        for card in self.cards:
            card.setVisible(not q or q in card.text)
        for header, keys in self.headers:
            header.setVisible(any(c.isVisible() for c in self.cards if c.key in keys) if q else True)

    def _choose(self, key):
        self.choice = key
        self.accept()

    def _toggle(self, key):
        self.pins = toggle_pin(self.pins, key)
        save_pins(self.settings, self.profile, self.pins)
        for card in self.cards:
            if card.key == key:
                card.set_pinned(key in self.pins)

    def _edit(self):
        self.edit_requested = True
        self.reject()
