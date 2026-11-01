"""QR code maker window (Morphix 1.10)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from i18n import tr

TIPS = {
    'drive': 'Google Drive: set sharing to “Anyone with the link” so people who scan can open the file.',
    'onedrive': 'OneDrive: share the file with “Anyone with the link” so people who scan can open it.',
    'dropbox': 'Dropbox: make sure the link is shared publicly so people who scan can open it.',
    'icloud': 'iCloud: share the file with “Anyone with the link” so people who scan can open it.',
}


def pil_to_pixmap(img):
    img = img.convert('RGBA')
    q = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(q)


class ColorButton(QPushButton):
    def __init__(self, color, on_change):
        super().__init__()
        self.color = color
        self.on_change = on_change
        self.setFixedSize(46, 30)
        self.clicked.connect(self._pick)
        self._paint()

    def _paint(self):
        self.setStyleSheet(f'QPushButton {{ background:{self.color}; border:2px solid #4F6F95; border-radius:8px; }}')

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.color), self, tr('Choose a colour'))
        if c.isValid():
            self.color = c.name()
            self._paint()
            self.on_change()


class QrDialog(QDialog):
    def __init__(self, parent=None, text=''):
        super().__init__(parent)
        from scan_dialog import STYLE
        import qr_maker
        self.qr = qr_maker
        self.settings = QSettings('Morphix', 'Morphix')
        self.setWindowTitle(tr('Morphix · QR code'))
        self.setStyleSheet(STYLE + 'QPlainTextEdit { background:#152C49; border:1px solid #31597F; border-radius:8px;'
                                   ' padding:6px; color:#EAF4FF; }'
                                   'QLabel#ok { color:#6EE7B7; font-weight:700; } QLabel#bad { color:#FCA5A5; font-weight:700; }'
                                   'QLabel#tip { color:#F4C66B; font-size:12px; }'
                                   'QFrame#preview { background:#FFFFFF; border-radius:16px; }')
        self.resize(940, 640)
        self.logo = None
        self._img = None
        self._timer = QTimer(self, singleShot=True, interval=150, timeout=self._update)

        root = QVBoxLayout(self); root.setContentsMargins(22, 18, 22, 16); root.setSpacing(10)
        title = QLabel(tr('QR code')); title.setObjectName('title'); root.addWidget(title)
        hint = QLabel(tr('Turn a link — Google Drive, OneDrive, a website — or a Wi-Fi network or contact card into '
                         'a QR code people can scan with their phone camera.'))
        hint.setObjectName('hint'); hint.setWordWrap(True); root.addWidget(hint)

        body = QHBoxLayout(); body.setSpacing(16); root.addLayout(body, 1)
        left = QVBoxLayout(); left.setSpacing(8)
        kinds = QHBoxLayout()
        self.kind = QButtonGroup(self)
        for i, label in enumerate((tr('Link or text'), tr('Wi-Fi'), tr('Contact'))):
            b = QPushButton(label); b.setObjectName('mode'); b.setCheckable(True)
            self.kind.addButton(b, i); kinds.addWidget(b)
        self.kind.button(0).setChecked(True)
        self.kind.idClicked.connect(self._kind)
        kinds.addStretch(); left.addLayout(kinds)

        self.pages = QStackedWidget()
        # link
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0)
        self.text = QPlainTextEdit(text)
        self.text.setPlaceholderText('https://drive.google.com/…')
        self.text.setFixedHeight(96)
        self.text.textChanged.connect(self._changed)
        l.addWidget(self.text)
        self.tip = QLabel(''); self.tip.setObjectName('tip'); self.tip.setWordWrap(True); l.addWidget(self.tip)
        l.addStretch(); self.pages.addWidget(w)
        # wifi
        w = QWidget(); g = QGridLayout(w); g.setContentsMargins(0, 0, 0, 0)
        self.ssid = QLineEdit(); self.wpass = QLineEdit(); self.wsec = QComboBox()
        for key, label in (('WPA', 'WPA / WPA2 / WPA3'), ('WEP', 'WEP'), ('nopass', tr('No password'))):
            self.wsec.addItem(label, key)
        self.whidden = QCheckBox(tr('Hidden network'))
        for r, (lab, wid) in enumerate(((tr('Network name'), self.ssid), (tr('Password'), self.wpass),
                                        (tr('Security'), self.wsec))):
            g.addWidget(QLabel(lab), r, 0); g.addWidget(wid, r, 1)
        g.addWidget(self.whidden, 3, 1)
        for wid in (self.ssid, self.wpass):
            wid.textChanged.connect(self._changed)
        self.wsec.currentIndexChanged.connect(self._changed); self.whidden.toggled.connect(self._changed)
        self.pages.addWidget(w)
        # contact
        w = QWidget(); g = QGridLayout(w); g.setContentsMargins(0, 0, 0, 0)
        self.cname, self.cphone, self.cemail, self.ccompany, self.cweb = (QLineEdit() for _ in range(5))
        for r, (lab, wid) in enumerate(((tr('Name'), self.cname), (tr('Phone'), self.cphone),
                                        (tr('Email'), self.cemail), (tr('Company'), self.ccompany),
                                        (tr('Website'), self.cweb))):
            g.addWidget(QLabel(lab), r, 0); g.addWidget(wid, r, 1)
            wid.textChanged.connect(self._changed)
        self.pages.addWidget(w)
        left.addWidget(self.pages)

        style = QFrame(); style.setObjectName('card')
        sg = QGridLayout(style); sg.setContentsMargins(14, 12, 14, 12); sg.setHorizontalSpacing(10)
        sec = QLabel(tr('LOOK')); sec.setObjectName('section'); sg.addWidget(sec, 0, 0, 1, 4)
        self.style_box = QComboBox()
        for key, label in (('rounded', 'Rounded'), ('dots', 'Dots'), ('square', 'Classic squares')):
            self.style_box.addItem(tr(label), key)
        self.style_box.setCurrentIndex(max(0, self.style_box.findData(self.settings.value('qr/style', 'rounded'))))
        self.style_box.currentIndexChanged.connect(self._changed)
        sg.addWidget(QLabel(tr('Shape')), 1, 0); sg.addWidget(self.style_box, 1, 1, 1, 3)
        self.fg = ColorButton(str(self.settings.value('qr/fg', '#0B1A2E')), self._changed)
        self.bg = ColorButton(str(self.settings.value('qr/bg', '#FFFFFF')), self._changed)
        sg.addWidget(QLabel(tr('Code colour')), 2, 0); sg.addWidget(self.fg, 2, 1)
        sg.addWidget(QLabel(tr('Background')), 2, 2); sg.addWidget(self.bg, 2, 3)
        self.transparent = QCheckBox(tr('Transparent background (PNG / SVG)'))
        self.transparent.toggled.connect(self._changed)
        sg.addWidget(self.transparent, 3, 0, 1, 4)
        self.logo_btn = QPushButton(tr('Add a logo in the middle…')); self.logo_btn.clicked.connect(self._pick_logo)
        self.logo_clear = QPushButton('✕'); self.logo_clear.setFixedWidth(40); self.logo_clear.clicked.connect(self._clear_logo)
        self.logo_clear.setEnabled(False)
        row = QHBoxLayout(); row.addWidget(self.logo_btn, 1); row.addWidget(self.logo_clear)
        sg.addLayout(row, 4, 0, 1, 4)
        self.caption = QLineEdit(); self.caption.setPlaceholderText(tr('For example: Scan to download'))
        self.caption.textChanged.connect(self._changed)
        sg.addWidget(QLabel(tr('Text under the code')), 5, 0); sg.addWidget(self.caption, 5, 1, 1, 3)
        left.addWidget(style)
        left.addStretch()
        body.addLayout(left, 1)

        right = QVBoxLayout(); right.setSpacing(8)
        frame = QFrame(); frame.setObjectName('preview'); frame.setFixedSize(360, 390)
        fl = QVBoxLayout(frame); fl.setContentsMargins(16, 16, 16, 16)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.preview)
        right.addWidget(frame, 0, Qt.AlignHCenter)
        self.check = QLabel(''); self.check.setAlignment(Qt.AlignCenter); self.check.setWordWrap(True)
        right.addWidget(self.check)
        right.addStretch()
        body.addLayout(right)

        foot = QHBoxLayout()
        self.size = QComboBox()
        for px in (512, 1024, 2048):
            self.size.addItem(f'{px} × {px} px', px)
        self.size.setCurrentIndex(1)
        foot.addWidget(QLabel(tr('PNG size'))); foot.addWidget(self.size)
        foot.addStretch()
        self.copy = QPushButton(tr('Copy')); self.copy.clicked.connect(self._copy)
        close = QPushButton(tr('Close')); close.clicked.connect(self.reject)
        self.save_btn = QPushButton(tr('Save…')); self.save_btn.setObjectName('primary'); self.save_btn.clicked.connect(self._save)
        foot.addWidget(self.copy); foot.addWidget(close); foot.addWidget(self.save_btn)
        root.addLayout(foot)
        self._update()

    # ------------------------------------------------------------------
    def _kind(self, index):
        self.pages.setCurrentIndex(index)
        self._changed()

    def _changed(self, *_):
        self._timer.start()

    def payload(self):
        k = self.kind.checkedId()
        if k == 1:
            if not self.ssid.text().strip():
                return ''
            return self.qr.wifi_payload(self.ssid.text().strip(), self.wpass.text(), self.wsec.currentData(),
                                        self.whidden.isChecked())
        if k == 2:
            fields = [w.text().strip() for w in (self.cname, self.cphone, self.cemail, self.ccompany, self.cweb)]
            if not any(fields):
                return ''
            return self.qr.contact_payload(*fields)
        return self.text.toPlainText().strip()

    def style(self):
        return {'style': self.style_box.currentData(), 'fg': self.fg.color, 'bg': self.bg.color,
                'transparent': self.transparent.isChecked(), 'logo': self.logo,
                'caption': self.caption.text().strip()}

    def _update(self):
        text = self.payload()
        tip = self.qr.link_tip(text) if self.kind.checkedId() == 0 else None
        self.tip.setText('ⓘ ' + tr(TIPS[tip]) if tip else '')
        enabled = bool(text)
        for b in (self.copy, self.save_btn):
            b.setEnabled(enabled)
        if not text:
            self._img = None
            self.preview.setText(tr('Your QR code appears here.'))
            self.preview.setStyleSheet('color:#6F89AA;')
            self.check.setText('')
            return
        self.preview.setStyleSheet('')
        try:
            self._img = self.qr.render(text, size=1024, **self.style())
        except Exception as exc:
            self._img = None
            self.preview.setText(str(exc))
            return
        self.preview.setPixmap(pil_to_pixmap(self._img).scaled(328, 358, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        back = self.qr.verify(self._img)
        if back == text:
            self.check.setObjectName('ok'); self.check.setText('✓ ' + tr('Checked: it scans correctly.'))
        elif back is None:
            self.check.setObjectName('hint'); self.check.setText('')
        else:
            self.check.setObjectName('bad')
            self.check.setText('⚠ ' + tr('Hard to scan — use darker code colour, a lighter background or a smaller logo.'))
        self.check.style().unpolish(self.check); self.check.style().polish(self.check)

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Choose a logo'), str(Path.home()),
                                              tr('Pictures') + ' (*.png *.jpg *.jpeg *.webp *.bmp)')
        if path:
            self.logo = path
            self.logo_btn.setText('✓ ' + Path(path).name)
            self.logo_clear.setEnabled(True)
            self._changed()

    def _clear_logo(self):
        self.logo = None
        self.logo_btn.setText(tr('Add a logo in the middle…'))
        self.logo_clear.setEnabled(False)
        self._changed()

    def _copy(self):
        text = self.payload()
        if text:
            img = self.qr.render(text, size=self.size.currentData(), **self.style())
            QApplication.clipboard().setPixmap(pil_to_pixmap(img))
            self.check.setText('✓ ' + tr('Copied — paste it into a document or message.'))

    def _save(self):
        text = self.payload()
        if not text:
            return
        self.settings.setValue('qr/style', self.style_box.currentData())
        self.settings.setValue('qr/fg', self.fg.color)
        self.settings.setValue('qr/bg', self.bg.color)
        start = Path(str(self.settings.value('qr/folder', str(Path.home() / 'Desktop'))))
        if not start.is_dir():
            start = Path.home()
        filters = 'PNG (*.png);;SVG (*.svg);;PDF (*.pdf)'
        path, chosen = QFileDialog.getSaveFileName(self, tr('Save the QR code'), str(start / 'QR code.png'), filters)
        if not path:
            return
        fmt = 'svg' if 'SVG' in chosen or path.lower().endswith('.svg') else \
              'pdf' if 'PDF' in chosen or path.lower().endswith('.pdf') else 'png'
        if not path.lower().endswith('.' + fmt):
            path += '.' + fmt
        try:
            self.qr.save(text, path, fmt, size=self.size.currentData(), **self.style())
        except Exception as exc:
            QMessageBox.warning(self, tr('QR code'), str(exc))
            return
        self.settings.setValue('qr/folder', str(Path(path).parent))
        self.check.setObjectName('ok')
        self.check.setText('✓ ' + tr('Saved: {name}', name=Path(path).name))
        self.check.style().unpolish(self.check); self.check.style().polish(self.check)
