"""Add-ons: optional components that are downloaded once and then work offline.

One place to see every downloadable part — its name, size, what it does,
whether it is installed — with Download / Remove buttons.
"""
from __future__ import annotations

import shutil
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
                               QProgressBar, QMessageBox, QDialog, QScrollArea)

from i18n import tr

LIBREOFFICE_URL = 'https://www.libreoffice.org/download/download-libreoffice/'


def catalogue():
    """Every optional component, in display order."""
    import transcription_engine as te
    import background_engine as be
    items = []
    speech_desc = {
        'fast': 'Quick drafts and clear recordings. Lowest accuracy.',
        'accurate': 'Good balance of speed and accuracy for everyday recordings.',
        'best': 'Highest accuracy — recommended for Arabic. Also powers “Maximum accuracy”.',
    }
    for key in ('fast', 'accurate', 'best'):
        alias, size, label = te.MODELS[key]
        items.append({
            'id': f'speech:{key}', 'group': 'Convert speech to text', 'title': label, 'size': size,
            'desc': speech_desc[key],
            'installed': lambda k=key: te.model_dir(k) is not None,
            'action': 'download_speech_model', 'options': {'quality': key},
            'remove': lambda a=alias: _remove(te.models_root() / a),
            'available': lambda: te.engine_available(),
            'unavailable': 'The speech engine is not installed. Run Launch_Morphix_Mac.command once while connected to the internet.',
        })
    bg_desc = {
        'standard': 'Clean cut-outs of people, products, animals and objects.',
        'best': 'Finest hair and fur edges. Needs a Mac with 16 GB of memory.',
    }
    for key in ('standard', 'best'):
        filename, size, label = be.MODELS[key][:3]
        items.append({
            'id': f'background:{key}', 'group': 'Remove the background', 'title': label, 'size': size,
            'desc': bg_desc[key],
            'installed': lambda k=key: be.model_path(k) is not None,
            'action': 'download_bg_model', 'options': {'bg_quality': key},
            'remove': lambda f=filename: _remove(be.models_root() / f),
            'available': lambda k=key: be.quality_allowed(k),
            'unavailable': 'This Mac does not have enough memory for this model (16 GB needed).',
        })
    from office_engine import find_office_engine
    items.append({
        'id': 'libreoffice', 'group': 'Office → PDF', 'title': 'LibreOffice', 'size': '≈ 350 MB',
        'desc': 'Free program that converts Word, PowerPoint and Excel files. Installed separately from its official website.',
        'installed': lambda: find_office_engine() is not None,
        'external': LIBREOFFICE_URL,
        'available': lambda: True,
    })
    return items


def _remove(path):
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


class AddonRow(QFrame):
    def __init__(self, item, owner):
        super().__init__()
        self.item, self.owner, self.job = item, owner, None
        self.setObjectName('addonCard')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)
        text = QVBoxLayout()
        text.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel(tr(item['title']))
        title.setObjectName('addonTitle')
        head.addWidget(title)
        size = QLabel(item['size'])
        size.setObjectName('addonSize')
        head.addWidget(size)
        head.addStretch(1)
        text.addLayout(head)
        desc = QLabel(tr(item['desc']))
        desc.setObjectName('addonDesc')
        desc.setWordWrap(True)
        text.addWidget(desc)
        self.state = QLabel()
        self.state.setObjectName('addonState')
        self.state.setWordWrap(True)
        text.addWidget(self.state)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.hide()
        text.addWidget(self.bar)
        lay.addLayout(text, 1)
        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        self.main = QPushButton()
        self.main.setObjectName('addonPrimary')
        self.main.setCursor(Qt.PointingHandCursor)
        self.main.setMinimumWidth(120)
        self.main.clicked.connect(self._main_clicked)
        buttons.addWidget(self.main)
        self.remove = QPushButton(tr('Remove'))
        self.remove.setObjectName('addonSecondary')
        self.remove.setCursor(Qt.PointingHandCursor)
        self.remove.clicked.connect(self._remove_clicked)
        buttons.addWidget(self.remove)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        self.refresh()

    def refresh(self):
        item = self.item
        busy = self.job is not None
        installed = item['installed']()
        available = item['available']()
        external = 'external' in item
        if busy:
            self.main.setText(tr('Cancel'))
            self.main.setEnabled(True)
            self.remove.hide()
            return
        self.bar.hide()
        if installed:
            self.state.setText('✓ ' + tr('Installed — works offline'))
            self.state.setProperty('ok', True)
            self.main.setText(tr('Installed'))
            self.main.setEnabled(False)
            self.remove.setVisible(not external)
        elif not available:
            self.state.setText(tr(item['unavailable']))
            self.state.setProperty('ok', False)
            self.main.setText(tr('Download'))
            self.main.setEnabled(False)
            self.remove.hide()
        else:
            self.state.setText(tr('Not installed — needs internet once') if not external
                               else tr('Not installed'))
            self.state.setProperty('ok', False)
            self.main.setText(tr('Open website') if external else tr('Download'))
            self.main.setEnabled(True)
            self.remove.hide()
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)

    def _main_clicked(self):
        if self.job is not None:
            self.job.cancel()
            return
        if 'external' in self.item:
            webbrowser.open(self.item['external'])
            return
        from conversion_job import ConversionJob
        import transcription_engine as te
        self.job = ConversionJob(self.item['action'], [], str(te.models_root()), dict(self.item['options']), parent=self)
        self.bar.show()
        self.bar.setRange(0, 0)
        self.state.setText(tr('Downloading…'))
        self.job.progress.connect(self._progress)
        self.job.status.connect(self.state.setText)
        self.job.failed.connect(self._failed)
        self.job.finished.connect(self._finished)
        self.job.start()
        self.refresh()

    def _progress(self, value):
        if 3 < value < 100:
            self.bar.setRange(0, 100)
            self.bar.setValue(value)

    def _failed(self, error):
        if error.strip() != 'Cancelled.':
            from main import _friendly_error
            QMessageBox.warning(self, tr('Download failed'), _friendly_error(error))

    def _finished(self):
        job, self.job = self.job, None
        if job is not None:
            job.deleteLater()
        self.refresh()

    def _remove_clicked(self):
        answer = QMessageBox.question(self, tr('Remove'),
                                      tr('Remove “{name}” from this computer? You can download it again at any time.',
                                         name=tr(self.item['title'])))
        if answer == QMessageBox.Yes:
            self.item['remove']()
            self.refresh()


ADDONS_CSS = '''
QFrame#addonCard { background:#10223A; border:1px solid #284B70; border-radius:14px; }
QFrame#addonCard QLabel { background:transparent; }
QLabel#addonTitle { color:#F2F8FF; font-size:15px; font-weight:700; }
QLabel#addonSize { color:#9CC8F5; background:#183659; border-radius:8px; padding:2px 8px; font-size:11px; font-weight:700; }
QLabel#addonDesc { color:#A9BFD9; font-size:12px; }
QLabel#addonState { color:#F4C66B; font-size:12px; font-weight:600; }
QLabel#addonState[ok="true"] { color:#8FF0D7; }
QLabel#addonGroup { color:#8DA6C6; font-size:12px; font-weight:700; padding-top:8px; }
QPushButton#addonPrimary { background:#247FE4; color:white; border:1px solid #4F9FF9; border-radius:9px; padding:8px 14px; font-weight:700; }
QPushButton#addonPrimary:disabled { background:#16324F; color:#8FB1D4; border-color:#244A70; }
QPushButton#addonSecondary { background:transparent; color:#C9DBF2; border:1px solid #31597F; border-radius:9px; padding:6px 12px; }
QProgressBar { background:#22344B; border:0; border-radius:3px; }
QProgressBar::chunk { background:#459EFC; border-radius:3px; }
'''


def addons_widget(parent=None):
    """The add-ons list (used by the Add-ons window and the Settings page)."""
    box = QWidget(parent)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    group = None
    box.rows = []
    for item in catalogue():
        if item['group'] != group:
            group = item['group']
            g = QLabel(tr(group))
            g.setObjectName('addonGroup')
            lay.addWidget(g)
        row = AddonRow(item, box)
        box.rows.append(row)
        lay.addWidget(row)
    lay.addStretch(1)
    box.setStyleSheet(ADDONS_CSS)
    return box


class AddonsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Morphix · Add-ons'))
        self.setMinimumSize(640, 620)
        self.setStyleSheet('QDialog { background:#0A1729; } QLabel { color:#E7F1FD; background:transparent; }'
                           'QScrollArea { border:0; background:transparent; }'
                           'QPushButton#close { background:#1A3455; color:#E7F1FD; border:1px solid #315C86;'
                           ' border-radius:9px; padding:9px 18px; }')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(8)
        title = QLabel(tr('Add-ons'))
        title.setStyleSheet('font-size:24px; font-weight:800; color:#FFFFFF;')
        lay.addWidget(title)
        intro = QLabel(tr('Extra tools that are downloaded once. After downloading they work without the internet. '
                          'Everything else in Morphix is already built in.'))
        intro.setWordWrap(True)
        intro.setStyleSheet('color:#9DB6D3; font-size:13px;')
        lay.addWidget(intro)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = addons_widget()
        inner.setStyleSheet(inner.styleSheet() + 'QWidget { background: transparent; }')
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton(tr('Close'))
        close.setObjectName('close')
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)

    def reject(self):
        self.accept()

    def accept(self):
        busy = [r for r in self.findChildren(AddonRow) if r.job is not None]
        if busy and QMessageBox.question(self, tr('Add-ons'),
                                         tr('A download is still running. Cancel it and close?')) != QMessageBox.Yes:
            return
        for r in busy:
            r.job.cancel()
        super().accept()
