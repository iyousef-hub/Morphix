"""Option windows for the Morphix 1.9 tools (shared by Studio and the Action Hub).

ask_action_options(key, paths, parent) → dict of options, {} when none are
needed, or None when the user cancelled.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QTransform, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox,
                               QFrame, QRadioButton, QButtonGroup, QSlider, QLineEdit, QPushButton,
                               QListWidget, QListWidgetItem, QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QMessageBox, QWidget,
                               QSizePolicy)

from i18n import tr, option_row

STYLE = """
QDialog { background:#0B1A2E; color:#EAF4FF; }
QLabel { color:#DCEBFC; background:transparent; }
QLabel#title { font-size:19px; font-weight:800; color:#FFFFFF; }
QLabel#hint { color:#93B2D3; font-size:12px; }
QLabel#cardTitle { font-size:15px; font-weight:800; color:#FFFFFF; }
QLabel#pro { color:#8FF0D7; font-size:12px; }
QLabel#con { color:#F4C66B; font-size:12px; }
QLabel#badge { color:#9CC8F5; background:#183659; border-radius:8px; padding:2px 8px; font-size:11px; font-weight:700; }
QComboBox, QLineEdit { background:#152C49; border:1px solid #31597F; border-radius:8px; padding:6px 10px; color:#EAF4FF; }
QFrame#card { background:#112440; border:1px solid #284A70; border-radius:12px; }
QFrame#card[selected="true"] { border:2px solid #4F9FF9; background:#14304F; }
QPushButton { color:#EAF4FF; background:#1A3555; border:1px solid #31597F; border-radius:9px; padding:8px 14px; font-weight:600; }
QPushButton:hover { background:#24496F; }
QPushButton:disabled { color:#6F89AA; }
QPushButton#primary { background:#247FE4; border-color:#55A3FB; color:white; }
QListWidget { background:#0E1F36; border:1px solid #284A70; border-radius:12px; padding:8px; color:#DCEBFC; outline:none; }
QListWidget::item { border-radius:8px; padding:4px; }
QListWidget::item:selected { background:#24518A; }
QSlider::groove:horizontal { height:6px; background:#22344B; border-radius:3px; }
QSlider::sub-page:horizontal { background:#459EFC; border-radius:3px; }
QSlider::handle:horizontal { background:#EAF4FF; width:16px; margin:-6px 0; border-radius:8px; }
"""


def _buttons(dialog, ok_text):
    box = QDialogButtonBox()
    ok = box.addButton(ok_text, QDialogButtonBox.AcceptRole)
    ok.setObjectName('primary')
    box.addButton(tr('Cancel'), QDialogButtonBox.RejectRole)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box, ok


def _base(dialog, title_text, info_text=None, width=520):
    dialog.setStyleSheet(STYLE)
    dialog.setMinimumWidth(width)
    lay = QVBoxLayout(dialog)
    lay.setContentsMargins(22, 20, 22, 18)
    lay.setSpacing(12)
    title = QLabel(title_text)
    title.setObjectName('title')
    lay.addWidget(title)
    if info_text:
        info = QLabel(info_text)
        info.setObjectName('hint')
        info.setWordWrap(True)
        lay.addWidget(info)
    return lay


# ===================================================================== PowerPoint
class PptDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.settings = QSettings('Morphix', 'Morphix')
        self.setWindowTitle(tr('Morphix · PowerPoint-ready'))
        lay = _base(self, tr('Make it PowerPoint-compatible'),
                    tr('Videos become MP4 (H.264 video + AAC sound) and audio becomes M4A or MP3 — the formats '
                       'PowerPoint plays on Windows and Mac. Your original files are not changed.'))
        card = QFrame(); card.setObjectName('card')
        form = QVBoxLayout(card); form.setContentsMargins(14, 12, 14, 12); form.setSpacing(8)
        row = QHBoxLayout(); row.addWidget(QLabel(tr('Video size')))
        self.size_box = QComboBox()
        for key, label in (('1080', 'Full HD (1080p) — recommended'), ('720', 'Smaller file (720p)'),
                           ('keep', 'Keep the original size')):
            self.size_box.addItem(tr(label), key)
        self.size_box.setCurrentIndex(max(0, self.size_box.findData(self.settings.value('ppt/height', '1080'))))
        row.addWidget(self.size_box, 1); form.addLayout(row)
        row = QHBoxLayout(); row.addWidget(QLabel(tr('Audio format')))
        self.audio = QComboBox()
        self.audio.addItem(tr('M4A (AAC) — recommended'), 'm4a')
        self.audio.addItem('MP3', 'mp3')
        self.audio.setCurrentIndex(max(0, self.audio.findData(self.settings.value('ppt/audio', 'm4a'))))
        row.addWidget(self.audio, 1); form.addLayout(row)
        lay.addWidget(card)
        box, _ = _buttons(self, tr('Convert'))
        lay.addWidget(box)

    def options(self):
        self.settings.setValue('ppt/height', self.size_box.currentData())
        self.settings.setValue('ppt/audio', self.audio.currentData())
        return {'ppt_height': self.size_box.currentData(), 'ppt_audio': self.audio.currentData()}


# ===================================================================== Trim
def _frame_pixmap(path, seconds, width=300):
    import subprocess
    import imageio_ffmpeg
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-ss', f'{seconds:.3f}',
           '-i', str(path), '-frames:v', '1', '-vf', f'scale={width}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-']
    try:
        data = subprocess.run(cmd, capture_output=True, timeout=15).stdout
    except Exception:
        return None
    image = QImage.fromData(data, 'PNG')
    return QPixmap.fromImage(image) if not image.isNull() else None


class TrimDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        import tools_engine as te
        self.path = path
        self.info = te.media_info(path)
        self.duration = max(0.1, self.info['duration'])
        self.setWindowTitle(tr('Morphix · Trim'))
        lay = _base(self, tr('Trim'), tr('Choose the part to keep. The original file is not changed.'), 560)
        name = QLabel(Path(path).name + '  ·  ' + tr('Length') + ' ' + te.format_time(self.duration)[:-4])
        name.setObjectName('hint'); lay.addWidget(name)
        self.thumbs = None
        if self.info['video']:
            holder = QWidget(); holder.setLayoutDirection(Qt.LeftToRight)
            self.thumbs = QHBoxLayout(holder); self.thumbs.setContentsMargins(0, 0, 0, 0)
            self.start_thumb, self.end_thumb = QLabel(), QLabel()
            for t in (self.start_thumb, self.end_thumb):
                t.setFixedSize(240, 136); t.setAlignment(Qt.AlignCenter)
                t.setStyleSheet('background:#071222; border:1px solid #284A70; border-radius:8px;')
                self.thumbs.addWidget(t)
            lay.addWidget(holder)
        card = QFrame(); card.setObjectName('card')
        form = QVBoxLayout(card); form.setContentsMargins(14, 12, 14, 12); form.setSpacing(8)
        self.start_slider, self.end_slider = QSlider(Qt.Horizontal), QSlider(Qt.Horizontal)
        self.start_edit, self.end_edit = QLineEdit(), QLineEdit()
        total_ms = int(self.duration * 1000)
        for label, slider, edit, value in ((tr('From'), self.start_slider, self.start_edit, 0),
                                           (tr('To'), self.end_slider, self.end_edit, total_ms)):
            slider.setRange(0, total_ms); slider.setValue(value)
            slider.setLayoutDirection(Qt.LeftToRight)  # time always runs left → right
            edit.setFixedWidth(130); edit.setText(te.format_time(value / 1000))
            edit.setLayoutDirection(Qt.LeftToRight)
            row = QHBoxLayout(); lab = QLabel(label); lab.setFixedWidth(40)
            row.addWidget(lab); row.addWidget(slider, 1); row.addWidget(edit)
            form.addLayout(row)
            slider.valueChanged.connect(lambda v, e=edit: e.setText(te.format_time(v / 1000)))
            slider.valueChanged.connect(self._update_length)
            slider.sliderReleased.connect(self._update_thumbs)
            edit.editingFinished.connect(lambda s=slider, e=edit: self._from_text(s, e))
        self.length = QLabel(); self.length.setObjectName('hint')
        form.addWidget(self.length)
        lay.addWidget(card)
        self.exact = QRadioButton(); self.fast = QRadioButton()
        self.exact.setChecked(True)
        lay.addWidget(option_row(self.exact, tr('Exact (re-encodes — cuts at the exact second)')))
        lay.addWidget(option_row(self.fast, tr('Fast (no re-encoding — video cuts at the nearest keyframe)')))
        box, _ = _buttons(self, tr('Trim'))
        lay.addWidget(box)
        self._update_length()
        QTimer.singleShot(50, self._update_thumbs)

    def _from_text(self, slider, edit):
        import tools_engine as te
        try:
            slider.setValue(int(te.parse_time(edit.text()) * 1000))
        except ValueError:
            edit.setText(te.format_time(slider.value() / 1000))
        self._update_thumbs()

    def _update_length(self, *_):
        import tools_engine as te
        a, b = self.start_slider.value(), self.end_slider.value()
        if b <= a:
            self.length.setText('⚠ ' + tr('The end time must be after the start time.'))
        else:
            self.length.setText(tr('Kept part') + ': ' + te.format_time((b - a) / 1000)[:-4])

    def _update_thumbs(self):
        if not self.thumbs:
            return
        for label, slider in ((self.start_thumb, self.start_slider), (self.end_thumb, self.end_slider)):
            t = min(slider.value() / 1000, max(0, self.duration - 0.05))
            pix = _frame_pixmap(self.path, t)
            if pix:
                label.setPixmap(pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self):
        if self.end_slider.value() <= self.start_slider.value():
            QMessageBox.warning(self, tr('Trim'), tr('The end time must be after the start time.'))
            return
        super().accept()

    def options(self):
        import tools_engine as te
        return {'trim_start': te.format_time(self.start_slider.value() / 1000),
                'trim_end': te.format_time(self.end_slider.value() / 1000),
                'trim_exact': self.exact.isChecked()}


# ===================================================================== OCR engine choice
OCR_ENGINES = (
    ('standard', 'Standard (built in)', 'Tesseract',
     ['Built in — nothing to download', 'Fast and light', 'Can also make searchable PDFs'],
     ['Weaker on photos, screenshots and small text', 'Mixed Arabic + English lines can come out jumbled']),
    ('accurate', 'Accurate (PaddleOCR)', 'PP-OCR',
     ['Much better on photos, screenshots, small and mixed text', 'Arabic and English',
      'Keeps the line order, right-to-left for Arabic'],
     ['Slower than Standard', 'Arabic needs a one-time download (≈ 8 MB)',
      'May skip some numbers inside Arabic lines', 'Gives a text file (not a searchable PDF)']),
    ('formula', 'Formulas → LaTeX', 'LaTeX-OCR',
     ['Turns printed math formulas into LaTeX', 'Saves Markdown ($$ … $$) and .tex files', 'Works offline'],
     ['One formula per image — crop the picture around the formula', 'One-time download (≈ 170 MB)',
      'Handwriting and very large formulas are less accurate', 'Images only']),
)


class OcrChoiceDialog(QDialog):
    def __init__(self, paths, key, parent=None):
        super().__init__(parent)
        import ocr_models as om
        self.settings = QSettings('Morphix', 'Morphix')
        self.images_only = all(Path(p).suffix.lower() != '.pdf' for p in paths)
        self.setWindowTitle(tr('Morphix · Extract text'))
        lay = _base(self, tr('Choose the text recognition (OCR)'),
                    tr('Everything runs on this computer. Pick the engine that suits your file.'), 640)
        from addons import ADDONS_CSS
        self.setStyleSheet(STYLE + ADDONS_CSS)
        self.group = QButtonGroup(self)
        self.cards = {}
        from addons import AddonRow, catalogue
        rows = {item['id']: item for item in catalogue()}
        for key_, title, engine, pros, cons in OCR_ENGINES:
            if key_ == 'formula' and not self.images_only:
                continue
            if key_ == 'accurate' and not om.accurate_available():
                continue
            card = QFrame(); card.setObjectName('card')
            v = QVBoxLayout(card); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(4)
            head = QHBoxLayout()
            radio = QRadioButton(); radio.setProperty('engine', key_)
            self.group.addButton(radio)
            head.addWidget(radio)
            t = QLabel(tr(title)); t.setObjectName('cardTitle'); head.addWidget(t)
            b = QLabel(engine); b.setObjectName('badge'); head.addWidget(b)
            head.addStretch(1)
            v.addLayout(head)
            for text in pros:
                l = QLabel('✓  ' + tr(text)); l.setObjectName('pro'); l.setWordWrap(True); v.addWidget(l)
            for text in cons:
                l = QLabel('–  ' + tr(text)); l.setObjectName('con'); l.setWordWrap(True); v.addWidget(l)
            if key_ == 'accurate':
                row = QHBoxLayout(); row.addWidget(QLabel(tr('Language')))
                self.lang = QComboBox()
                self.lang.addItem(tr('Arabic + English'), 'ar')
                self.lang.addItem(tr('English & other Latin languages'), 'latin')
                self.lang.setCurrentIndex(0 if om.arabic_model() else 1)
                row.addWidget(self.lang, 1); v.addLayout(row)
                if 'ocr:arabic' in rows:
                    v.addWidget(self._compact(AddonRow(rows['ocr:arabic'], self)))
            if key_ == 'formula' and 'ocr:formula' in rows:
                v.addWidget(self._compact(AddonRow(rows['ocr:formula'], self)))
            card.mousePressEvent = lambda _e, r=radio: r.setChecked(True)
            self.cards[key_] = (card, radio)
            lay.addWidget(card)
        self.group.buttonToggled.connect(self._mark)
        last = self.settings.value('ocr/engine', 'standard')
        (self.cards.get(last) or self.cards['standard'])[1].setChecked(True)
        box, _ = _buttons(self, tr('Extract text'))
        lay.addWidget(box)

    @staticmethod
    def _compact(row):
        desc = row.findChild(QLabel, 'addonDesc')
        if desc:
            desc.hide()
        return row

    def _mark(self, *_):
        for card, radio in self.cards.values():
            card.setProperty('selected', radio.isChecked())
            card.style().unpolish(card); card.style().polish(card)

    def engine(self):
        b = self.group.checkedButton()
        return b.property('engine') if b else 'standard'

    def accept(self):
        import ocr_models as om
        e = self.engine()
        if e == 'accurate' and getattr(self, 'lang', None) and self.lang.currentData() == 'ar' and not om.arabic_model():
            QMessageBox.information(self, tr('Extract text'), tr('Download the Arabic model first (one time), '
                                                                 'or choose “English & other Latin languages”.'))
            return
        if e == 'formula' and not om.formula_dir():
            QMessageBox.information(self, tr('Extract text'), tr('Download the formula model first (one time).'))
            return
        super().accept()

    def options(self):
        e = self.engine()
        self.settings.setValue('ocr/engine', e)
        out = {'ocr_engine': e}
        if e == 'accurate':
            out['ocr_lang'] = self.lang.currentData()
        return out


# ===================================================================== organize pages
class _ThumbDelegate(QStyledItemDelegate):
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self._size = size

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.decorationPosition = QStyleOptionViewItem.Top
        option.decorationAlignment = Qt.AlignHCenter | Qt.AlignVCenter
        option.displayAlignment = Qt.AlignHCenter | Qt.AlignTop

    def sizeHint(self, option, index):
        return self._size


class PageOrganizer(QDialog):
    THUMB = QSize(132, 180)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        import pymupdf as fitz
        self.path = str(path)
        self.doc = fitz.open(self.path)
        if self.doc.needs_pass:
            self.doc.close()
            raise ValueError(tr('Password-protected PDF is not supported by the visual editor.'))
        self.setWindowTitle(tr('Morphix · Organize pages'))
        self.resize(980, 720)
        lay = _base(self, tr('Organize pages'),
                    tr('Drag pages to reorder them. Select one or more pages to rotate or delete them. '
                       'A new PDF is saved; the original is not changed.'), 760)
        self.list = QListWidget()
        # List mode + wrapping looks like a grid but reorders the pages on drop
        # (icon mode would only move the picture around).
        self.list.setViewMode(QListWidget.ListMode)
        self.list.setFlow(QListWidget.LeftToRight)
        self.list.setWrapping(True)
        self.list.setUniformItemSizes(True)
        self.list.setIconSize(self.THUMB)
        self.list.setItemDelegate(_ThumbDelegate(QSize(self.THUMB.width() + 28, self.THUMB.height() + 40), self.list))
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setDropIndicatorShown(True)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setWordWrap(True)
        self.list.setSpacing(6)
        self.list.setLayoutDirection(Qt.LeftToRight)  # page 1 first, in reading order of a grid
        lay.addWidget(self.list, 1)
        tools = QHBoxLayout()
        for text, cb in ((tr('↺ Rotate left'), lambda: self.rotate(-90)), (tr('↻ Rotate right'), lambda: self.rotate(90)),
                         (tr('Delete'), self.delete), (tr('Select all'), self.list.selectAll),
                         (tr('Reverse order'), self.reverse)):
            b = QPushButton(text); b.clicked.connect(cb); tools.addWidget(b)
        tools.addStretch(1)
        self.count = QLabel(); self.count.setObjectName('hint'); tools.addWidget(self.count)
        lay.addLayout(tools)
        box, _ = _buttons(self, tr('Save as a new PDF'))
        lay.addWidget(box)
        QShortcut(QKeySequence.Delete, self.list, activated=self.delete)
        QShortcut(QKeySequence(Qt.Key_Backspace), self.list, activated=self.delete)
        for i in range(len(self.doc)):
            item = QListWidgetItem(str(i + 1))
            item.setData(Qt.UserRole, [i, 0])
            item.setTextAlignment(Qt.AlignHCenter)
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled)
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)
            self.list.addItem(item)
        self._pending = list(range(len(self.doc)))
        self._base_pix = {}
        self._render_next()
        self.list.model().rowsMoved.connect(self._renumber)
        self._renumber()

    def _render_next(self):
        if not self._pending:
            return
        import pymupdf as fitz
        for _ in range(6):
            if not self._pending:
                break
            i = self._pending.pop(0)
            page = self.doc[i]
            zoom = min(self.THUMB.width() / page.rect.width, self.THUMB.height() / page.rect.height) * 2
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
            self._base_pix[i] = QPixmap.fromImage(image)
            for row in range(self.list.count()):
                item = self.list.item(row)
                if item.data(Qt.UserRole)[0] == i:
                    self._apply_icon(item)
        QTimer.singleShot(0, self._render_next)

    def _apply_icon(self, item):
        index, rotation = item.data(Qt.UserRole)
        pix = self._base_pix.get(index)
        if pix is None:
            return
        if rotation:
            pix = pix.transformed(QTransform().rotate(rotation), Qt.SmoothTransformation)
        from PySide6.QtGui import QIcon
        icon = QIcon()
        icon.addPixmap(pix, QIcon.Normal)
        icon.addPixmap(pix, QIcon.Selected)
        item.setIcon(icon)

    def _renumber(self, *_):
        for row in range(self.list.count()):
            item = self.list.item(row)
            index, rotation = item.data(Qt.UserRole)
            mark = f' ↻{rotation}°' if rotation else ''
            item.setText(f'{row + 1}' + (f'  ({tr("was")} {index + 1})' if index != row else '') + mark)
        self.count.setText(tr('{n} page(s)', n=self.list.count()))

    def rotate(self, degrees):
        for item in self.list.selectedItems():
            index, rotation = item.data(Qt.UserRole)
            item.setData(Qt.UserRole, [index, (rotation + degrees) % 360])
            self._apply_icon(item)
        self._renumber()

    def delete(self):
        selected = self.list.selectedItems()
        if not selected:
            return
        if len(selected) >= self.list.count():
            QMessageBox.warning(self, tr('Cannot remove'), tr('A PDF must contain at least one page.'))
            return
        for item in selected:
            self.list.takeItem(self.list.row(item))
        self._renumber()

    def reverse(self):
        items = [self.list.takeItem(0) for _ in range(self.list.count())]
        for item in reversed(items):
            self.list.addItem(item)
        self._renumber()

    def options(self):
        return {'pages': [self.list.item(r).data(Qt.UserRole) for r in range(self.list.count())]}

    def done(self, result):
        try:
            self.doc.close()
        except Exception:
            pass
        super().done(result)


# ===================================================================== entry point
def ask_action_options(key, paths, parent=None):
    """Options for the 1.9 tools. Returns {} (no options), a dict, or None (cancelled)."""
    dialog = None
    if key == 'ppt_media':
        dialog = PptDialog(paths, parent)
    elif key == 'trim_media':
        dialog = TrimDialog(paths[0], parent)
    elif key == 'organize_pdf':
        dialog = PageOrganizer(paths[0], parent)
    elif key in ('sign_pdf', 'sign_images'):
        from signature_dialog import SignatureDialog
        dialog = SignatureDialog(paths, 'pdf' if key == 'sign_pdf' else 'image', parent)
    elif key in ('ocr_image_text', 'extract_pdf_text', 'ocr_pdf_text'):
        dialog = OcrChoiceDialog(paths, key, parent)
    if dialog is None:
        return {}
    dialog.setWindowFlag(Qt.WindowStaysOnTopHint, parent is None)
    if dialog.exec() != QDialog.Accepted:
        return None
    return dialog.options()
