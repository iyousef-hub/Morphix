"""Signature window: draw / upload / pick a saved signature, then place it.

Returns (via .options()):
    {'signature': <png path>, 'box': [x, y, w], 'pages': spec, 'page_index': n}
box is relative to the displayed page / image (top-left origin); the height
follows the signature's aspect ratio.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QSettings, Signal, QSize
from PySide6.QtGui import (QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QIcon, QBrush, QCursor)
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QStackedWidget,
                               QTabWidget, QSlider, QComboBox, QFileDialog, QListWidget, QListWidgetItem,
                               QCheckBox, QLineEdit, QSpinBox, QMessageBox, QColorDialog, QButtonGroup,
                               QToolButton, QFrame, QApplication)

from i18n import tr, option_row

INK = (('#111111', 'Black'), ('#1A3FA8', 'Blue'), ('#0B2A6B', 'Navy'), ('#B3261E', 'Red'), ('#1E6B3A', 'Green'))


def signatures_dir() -> Path:
    from transcription_engine import models_root
    folder = models_root().parent / 'signatures'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _checker(size=12):
    pix = QPixmap(size * 2, size * 2)
    pix.fill(QColor('#FFFFFF'))
    p = QPainter(pix)
    p.fillRect(0, 0, size, size, QColor('#E9EEF5'))
    p.fillRect(size, size, size, size, QColor('#E9EEF5'))
    p.end()
    return QBrush(pix)


# --------------------------------------------------------------------- drawing pad
class SignaturePad(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 230)
        self.setCursor(Qt.CrossCursor)
        self.strokes = []      # [(QColor, width, [QPointF…])] in widget coordinates
        self.color = QColor(INK[1][0])
        self.pen_width = 3.0

    def clear(self):
        self.strokes.clear()
        self.update(); self.changed.emit()

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self.update(); self.changed.emit()

    def is_empty(self):
        return not any(len(s[2]) > 1 for s in self.strokes) and not self.strokes

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.strokes.append((QColor(self.color), self.pen_width, [e.position()]))
            self.update()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self.strokes:
            pts = self.strokes[-1][2]
            p = e.position()
            if (p - pts[-1]).manhattanLength() >= 1.5:
                pts.append(p)
                self.update()

    def mouseReleaseEvent(self, e):
        if self.strokes:
            self.changed.emit()

    @staticmethod
    def _path(points, scale=1.0, offset=QPointF(0, 0)):
        pts = [(p - offset) * scale for p in points]
        path = QPainterPath(pts[0])
        if len(pts) == 1:
            path.addEllipse(pts[0], 0.1, 0.1)
            return path
        for a, b in zip(pts[1:-1], pts[2:]):
            path.quadTo(a, (a + b) / 2)
        path.lineTo(pts[-1])
        return path

    def _draw(self, painter, scale=1.0, offset=QPointF(0, 0)):
        painter.setRenderHint(QPainter.Antialiasing)
        for color, width, pts in self.strokes:
            pen = QPen(color, width * scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            if len(pts) == 1:
                painter.setBrush(color); painter.setPen(Qt.NoPen)
                painter.drawEllipse((pts[0] - offset) * scale, width * scale / 2, width * scale / 2)
            else:
                painter.drawPath(self._path(pts, scale, offset))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor('#C9D6E6'), 1))
        p.setBrush(QColor('#FFFFFF'))
        p.drawRoundedRect(r, 12, 12)
        base = r.bottom() - r.height() * 0.28
        p.setPen(QPen(QColor('#B8C6D8'), 1, Qt.DashLine))
        p.drawLine(QPointF(r.left() + 28, base), QPointF(r.right() - 28, base))
        p.setPen(QColor('#9AAAC0'))
        p.drawText(QRectF(r.left() + 28, base + 4, 200, 20), Qt.AlignLeft, '✕')
        if not self.strokes:
            p.setPen(QColor('#9AAAC0'))
            p.drawText(r, Qt.AlignCenter, tr('Sign here with the mouse or trackpad'))
        self._draw(p)
        p.end()

    def export(self, dest, scale=3.0):
        """Transparent PNG, cropped to the ink."""
        if not self.strokes:
            return None
        xs = [pt.x() for _c, _w, pts in self.strokes for pt in pts]
        ys = [pt.y() for _c, _w, pts in self.strokes for pt in pts]
        pad = max(w for _c, w, _p in self.strokes) + 6
        left, top = min(xs) - pad, min(ys) - pad
        w, h = max(xs) - left + pad, max(ys) - top + pad
        image = QImage(int(w * scale) + 2, int(h * scale) + 2, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        p = QPainter(image)
        self._draw(p, scale, QPointF(left, top))
        p.end()
        image.save(str(dest), 'PNG')
        return Path(dest)


# --------------------------------------------------------------------- preview of a transparent PNG
class SignaturePreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 200)
        self.setAlignment(Qt.AlignCenter)
        self.path = None
        self.empty_text = tr('No signature yet')

    def set_path(self, path):
        self.path = Path(path) if path else None
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor('#C9D6E6'), 1))
        p.setBrush(_checker())
        p.drawRoundedRect(r, 12, 12)
        if self.path and self.path.exists():
            pix = QPixmap(str(self.path))
            target = r.adjusted(20, 20, -20, -20)
            s = pix.size().scaled(target.size().toSize(), Qt.KeepAspectRatio)
            if pix.width() < target.width() and pix.height() < target.height():
                s = pix.size()
            x = target.center().x() - s.width() / 2
            y = target.center().y() - s.height() / 2
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawPixmap(QRectF(x, y, s.width(), s.height()), pix, QRectF(pix.rect()))
        else:
            p.setPen(QColor('#7D8DA3'))
            p.drawText(r, Qt.AlignCenter, self.empty_text)
        p.end()


# --------------------------------------------------------------------- placement
class PlacementView(QWidget):
    """Shows the page / image and the signature; drag to move, drag the corner to resize."""
    moved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 460)
        self.setMouseTracking(True)
        self.page = QPixmap()
        self.sig = QPixmap()
        self.box = [0.60, 0.80, 0.28]
        self._drag = None

    def set_page(self, pix):
        self.page = pix
        self.update()

    def set_signature(self, path):
        self.sig = QPixmap(str(path))
        self._clamp()
        self.update()

    def _page_rect(self):
        if self.page.isNull():
            return QRectF(self.rect()).adjusted(20, 20, -20, -20)
        area = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        s = self.page.size().scaled(area.size().toSize(), Qt.KeepAspectRatio)
        return QRectF(area.center().x() - s.width() / 2, area.center().y() - s.height() / 2, s.width(), s.height())

    def _ratio(self):
        return self.sig.height() / max(1, self.sig.width()) if not self.sig.isNull() else 0.4

    def _sig_rect(self):
        pr = self._page_rect()
        x, y, w = self.box
        width = w * pr.width()
        return QRectF(pr.left() + x * pr.width(), pr.top() + y * pr.height(), width, width * self._ratio())

    def _clamp(self):
        pr = self._page_rect()
        x, y, w = self.box
        w = max(0.03, min(1.0, w))
        h_frac = w * pr.width() * self._ratio() / max(1, pr.height())
        if h_frac > 1:
            w /= h_frac
            h_frac = 1
        x = max(0.0, min(1.0 - w, x))
        y = max(0.0, min(1.0 - h_frac, y))
        self.box = [x, y, w]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor('#071222'))
        pr = self._page_rect()
        if not self.page.isNull():
            p.fillRect(pr.adjusted(3, 3, 3, 3), QColor(0, 0, 0, 90))
            p.drawPixmap(pr, self.page, QRectF(self.page.rect()))
        if not self.sig.isNull():
            sr = self._sig_rect()
            p.drawPixmap(sr, self.sig, QRectF(self.sig.rect()))
            p.setPen(QPen(QColor('#3D8BFD'), 1.4, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(sr)
            handle = QRectF(sr.right() - 7, sr.bottom() - 7, 14, 14)
            p.setPen(QPen(QColor('#FFFFFF'), 1.5))
            p.setBrush(QColor('#247FE4'))
            p.drawEllipse(handle)
        p.end()

    def _handle_hit(self, pos):
        sr = self._sig_rect()
        return (QPointF(sr.right(), sr.bottom()) - pos).manhattanLength() < 16

    def mousePressEvent(self, e):
        pos = e.position()
        sr = self._sig_rect()
        pr = self._page_rect()
        if self._handle_hit(pos):
            self._drag = ('resize', pos, list(self.box))
        elif sr.contains(pos):
            self._drag = ('move', pos, list(self.box))
        elif pr.contains(pos):
            # click on the page: move the signature there (centred on the pointer)
            x, y, w = self.box
            h = sr.height() / pr.height()
            self.box = [(pos.x() - pr.left()) / pr.width() - w / 2, (pos.y() - pr.top()) / pr.height() - h / 2, w]
            self._clamp(); self.update(); self.moved.emit()
            self._drag = ('move', pos, list(self.box))

    def mouseMoveEvent(self, e):
        pos = e.position()
        if not self._drag:
            self.setCursor(Qt.SizeFDiagCursor if self._handle_hit(pos)
                           else Qt.SizeAllCursor if self._sig_rect().contains(pos) else Qt.ArrowCursor)
            return
        kind, start, box = self._drag
        pr = self._page_rect()
        dx = (pos.x() - start.x()) / pr.width()
        dy = (pos.y() - start.y()) / pr.height()
        if kind == 'move':
            self.box = [box[0] + dx, box[1] + dy, box[2]]
        else:
            self.box = [box[0], box[1], box[2] + dx]
        self._clamp(); self.update(); self.moved.emit()

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def resizeEvent(self, e):
        self._clamp()
        super().resizeEvent(e)


def _pdf_page_pixmap(path, index, width=900):
    import pymupdf as fitz
    with fitz.open(path) as doc:
        page = doc[max(0, min(len(doc) - 1, index))]
        zoom = width / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(image)


def _image_pixmap(path, width=900):
    from PIL import Image, ImageOps
    from tools_engine import register_heic
    register_heic()
    with Image.open(path) as original:
        im = ImageOps.exif_transpose(original).convert('RGBA')
    im.thumbnail((width * 2, width * 2))
    data = im.tobytes('raw', 'RGBA')
    image = QImage(data, im.width, im.height, im.width * 4, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(image)


def _pdf_page_count(path):
    import pymupdf as fitz
    with fitz.open(path) as doc:
        if doc.needs_pass:
            raise ValueError(tr('Password-protected PDF is not supported by the visual editor.'))
        return len(doc)


# --------------------------------------------------------------------- dialog
class SignatureDialog(QDialog):
    def __init__(self, paths, kind='pdf', parent=None):
        super().__init__(parent)
        from action_dialogs import STYLE
        self.paths = [str(p) for p in paths]
        self.kind = kind
        self.settings = QSettings('Morphix', 'Morphix')
        self.tmp = Path(tempfile.gettempdir()) / f'morphix_sig_{int(time.time() * 1000)}'
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.uploaded = None
        self.saved_choice = None
        self.signature = None
        self.preview_index = 0
        if kind == 'pdf':
            self.page_count = _pdf_page_count(self.paths[0])
        self.setWindowTitle(tr('Morphix · Signature'))
        self.setStyleSheet(STYLE + """
            QTabWidget::pane { border:0; }
            QTabBar::tab { background:#132A47; color:#B9CEE6; padding:8px 18px; border-radius:8px; margin:0 3px; }
            QTabBar::tab:selected { background:#247FE4; color:white; }
            QToolButton#ink { border:2px solid #31597F; border-radius:14px; min-width:24px; min-height:24px; }
            QToolButton#ink:checked { border:3px solid #FFFFFF; }
            QSpinBox { background:#152C49; border:1px solid #31597F; border-radius:8px; padding:5px 8px; color:#EAF4FF; }
        """)
        self.resize(760, 640)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName('title')
        root.addWidget(self.title)
        self.hint = QLabel(); self.hint.setObjectName('hint'); self.hint.setWordWrap(True)
        root.addWidget(self.hint)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_step1())
        self.stack.addWidget(self._build_step2())
        row = QHBoxLayout()
        self.back = QPushButton(tr('Back'))
        self.back.clicked.connect(lambda: self._go(0))
        row.addWidget(self.back)
        row.addStretch(1)
        cancel = QPushButton(tr('Cancel')); cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        self.next = QPushButton(); self.next.setObjectName('primary')
        self.next.clicked.connect(self._next)
        row.addWidget(self.next)
        root.addLayout(row)
        start = 2 if self._saved_files() else 0
        self.tabs.setCurrentIndex(start)
        self._go(0)

    # ---------------- step 1
    def _build_step1(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._draw_tab(), tr('Draw'))
        self.tabs.addTab(self._upload_tab(), tr('Upload a picture'))
        self.tabs.addTab(self._saved_tab(), tr('Saved signatures'))
        lay.addWidget(self.tabs, 1)
        self.remember = QCheckBox()
        self.remember.setChecked(self.settings.value('sign/remember', True, type=bool))
        lay.addWidget(option_row(self.remember, tr('Save this signature on this computer for next time')))
        return page

    def _draw_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 10, 0, 0); lay.setSpacing(10)
        self.pad = SignaturePad()
        lay.addWidget(self.pad, 1)
        tools = QHBoxLayout(); tools.setSpacing(8)
        tools.addWidget(QLabel(tr('Ink')))
        self.ink_group = QButtonGroup(self)
        saved_ink = self.settings.value('sign/ink', INK[1][0])
        for color, name in INK:
            b = QToolButton(); b.setObjectName('ink'); b.setCheckable(True); b.setToolTip(tr(name))
            b.setStyleSheet(f'QToolButton#ink {{ background:{color}; }}')
            b.clicked.connect(lambda _=False, c=color: self._set_ink(c))
            self.ink_group.addButton(b)
            tools.addWidget(b)
            if color == saved_ink:
                b.setChecked(True)
        more = QPushButton(tr('Other colour…')); more.clicked.connect(self._pick_ink)
        tools.addWidget(more)
        tools.addSpacing(12)
        tools.addWidget(QLabel(tr('Thickness')))
        self.thick = QSlider(Qt.Horizontal); self.thick.setRange(1, 12); self.thick.setFixedWidth(120)
        self.thick.setValue(int(self.settings.value('sign/width', 3)))
        self.thick.valueChanged.connect(lambda v: setattr(self.pad, 'pen_width', float(v)))
        tools.addWidget(self.thick)
        tools.addStretch(1)
        undo = QPushButton(tr('Undo')); undo.clicked.connect(self.pad.undo); tools.addWidget(undo)
        clear = QPushButton(tr('Clear')); clear.clicked.connect(self.pad.clear); tools.addWidget(clear)
        lay.addLayout(tools)
        self.pad.color = QColor(saved_ink)
        self.pad.pen_width = float(self.thick.value())
        return w

    def _set_ink(self, color):
        self.pad.color = QColor(color)
        self.settings.setValue('sign/ink', color)

    def _pick_ink(self):
        c = QColorDialog.getColor(self.pad.color, self, tr('Ink'))
        if c.isValid():
            for b in self.ink_group.buttons():
                b.setChecked(False)
            self._set_ink(c.name())

    def _upload_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 10, 0, 0); lay.setSpacing(10)
        top = QHBoxLayout()
        choose = QPushButton(tr('Choose a picture…')); choose.setObjectName('primary')
        choose.clicked.connect(self._choose_upload)
        top.addWidget(choose)
        info = QLabel(tr('A photo or scan of your signature on white paper, or a transparent PNG.'))
        info.setObjectName('hint'); info.setWordWrap(True)
        top.addWidget(info, 1)
        lay.addLayout(top)
        self.upload_preview = SignaturePreview()
        self.upload_preview.empty_text = tr('No picture chosen')
        lay.addWidget(self.upload_preview, 1)
        tools = QHBoxLayout(); tools.setSpacing(8)
        self.remove_bg = QCheckBox()
        self.remove_bg.setChecked(True)
        tools.addWidget(option_row(self.remove_bg, tr('Remove the paper background'), wrap=False))
        tools.addSpacing(8)
        tools.addWidget(QLabel(tr('Strength')))
        self.threshold = QSlider(Qt.Horizontal); self.threshold.setRange(120, 245); self.threshold.setValue(200)
        self.threshold.setFixedWidth(130)
        tools.addWidget(self.threshold)
        tools.addWidget(QLabel(tr('Ink')))
        self.recolor = QComboBox()
        self.recolor.addItem(tr('Keep the original colour'), '')
        for color, name in INK:
            self.recolor.addItem(tr(name), color)
        tools.addWidget(self.recolor)
        tools.addStretch(1)
        lay.addLayout(tools)
        ai_row = QHBoxLayout()
        self.ai = QPushButton(tr('Remove background with AI'))
        self.ai.setToolTip(tr('Uses the “Remove the background” add-on — best for signatures on coloured or textured paper.'))
        self.ai.clicked.connect(self._ai_clean)
        ai_row.addWidget(self.ai)
        self.ai_note = QLabel(); self.ai_note.setObjectName('hint'); self.ai_note.setWordWrap(True)
        ai_row.addWidget(self.ai_note, 1)
        lay.addLayout(ai_row)
        for sig in (self.remove_bg.toggled, self.recolor.currentIndexChanged):
            sig.connect(self._process_upload)
        self.threshold.sliderReleased.connect(self._process_upload)
        self._refresh_ai()
        return w

    def _refresh_ai(self):
        try:
            import background_engine as be
            ok = be.model_path('standard') is not None or be.model_path('best') is not None
        except Exception:
            ok = False
        self.ai.setEnabled(ok and self.uploaded is not None)
        self.ai_note.setText('' if ok else tr('Download “Remove the background” from Add-ons to use AI cleanup.'))

    def _choose_upload(self):
        start = self.settings.value('sign/upload_dir', str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, tr('Choose a picture…'), start,
                                              tr('Images') + ' (*.png *.jpg *.jpeg *.heic *.heif *.webp *.tif *.tiff *.bmp)')
        if not path:
            return
        self.settings.setValue('sign/upload_dir', str(Path(path).parent))
        self.uploaded = Path(path)
        from PIL import Image
        try:
            with Image.open(path) as im:
                has_alpha = im.mode in ('RGBA', 'LA', 'PA') and im.getchannel('A').getextrema()[0] < 250
        except Exception:
            has_alpha = False
        self.remove_bg.setChecked(not has_alpha)
        self._process_upload()
        self._refresh_ai()

    def _process_upload(self, *_):
        if not self.uploaded:
            return
        import tools_engine as te
        dest = self.tmp / f'upload_{int(time.time() * 1000)}.png'
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.remove_bg.isChecked():
                te.clean_signature(self.uploaded, dest, threshold=self.threshold.value(),
                                   color=self.recolor.currentData() or None)
            else:
                from PIL import Image, ImageOps
                te.register_heic()
                with Image.open(self.uploaded) as im:
                    ImageOps.exif_transpose(im).convert('RGBA').save(dest)
                te.trim_transparent(dest)
                if self.recolor.currentData():
                    self._recolor(dest, self.recolor.currentData())
        except Exception as exc:
            QMessageBox.warning(self, tr('Signature'), str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.upload_preview.set_path(dest)

    @staticmethod
    def _recolor(path, color):
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert('RGBA')
        solid = Image.new('RGBA', im.size, color)
        solid.putalpha(im.getchannel('A'))
        solid.save(path)

    def _ai_clean(self):
        if not self.uploaded:
            return
        import background_engine as be
        import tools_engine as te
        out_dir = self.tmp / f'ai_{int(time.time() * 1000)}'
        out_dir.mkdir()
        quality = 'standard' if be.model_path('standard') else 'best'
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            outs = be.remove_background([str(self.uploaded)], str(out_dir), quality=quality)
            dest = Path(outs[0])
            te.trim_transparent(dest)
            if self.recolor.currentData():
                self._recolor(dest, self.recolor.currentData())
        except Exception as exc:
            QMessageBox.warning(self, tr('Signature'), str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.remove_bg.blockSignals(True); self.remove_bg.setChecked(False); self.remove_bg.blockSignals(False)
        self.upload_preview.set_path(dest)

    def _saved_files(self):
        return sorted(signatures_dir().glob('*.png'), key=lambda p: p.stat().st_mtime, reverse=True)

    def _saved_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 10, 0, 0); lay.setSpacing(10)
        self.saved = QListWidget()
        self.saved.setViewMode(QListWidget.IconMode)
        self.saved.setIconSize(QSize(200, 90))
        self.saved.setGridSize(QSize(224, 116))
        self.saved.setResizeMode(QListWidget.Adjust)
        self.saved.setMovement(QListWidget.Static)
        self.saved.setStyleSheet('QListWidget { background:#FFFFFF; } QListWidget::item:selected { background:#CFE3FF; }')
        self.saved.itemDoubleClicked.connect(lambda _i: self._next())
        lay.addWidget(self.saved, 1)
        row = QHBoxLayout()
        self.saved_empty = QLabel(tr('No saved signatures yet. Draw or upload one and keep “Save … for next time” ticked.'))
        self.saved_empty.setObjectName('hint'); self.saved_empty.setWordWrap(True)
        row.addWidget(self.saved_empty, 1)
        delete = QPushButton(tr('Delete')); delete.clicked.connect(self._delete_saved)
        row.addWidget(delete)
        lay.addLayout(row)
        self._fill_saved()
        return w

    def _fill_saved(self):
        self.saved.clear()
        files = self._saved_files()
        for f in files:
            item = QListWidgetItem(QIcon(str(f)), '')
            item.setData(Qt.UserRole, str(f))
            self.saved.addItem(item)
        if files:
            self.saved.setCurrentRow(0)
        self.saved_empty.setVisible(not files)

    def _delete_saved(self):
        item = self.saved.currentItem()
        if item and QMessageBox.question(self, tr('Delete'), tr('Delete this saved signature?')) == QMessageBox.Yes:
            Path(item.data(Qt.UserRole)).unlink(missing_ok=True)
            self._fill_saved()

    def _current_signature(self):
        tab = self.tabs.currentIndex()
        if tab == 0:
            if not self.pad.strokes:
                return None, True
            return self.pad.export(self.tmp / f'drawn_{int(time.time() * 1000)}.png'), True
        if tab == 1:
            return self.upload_preview.path, True
        item = self.saved.currentItem()
        return (Path(item.data(Qt.UserRole)) if item else None), False

    # ---------------- step 2
    def _build_step2(self):
        page = QWidget()
        lay = QHBoxLayout(page); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(14)
        self.view = PlacementView()
        lay.addWidget(self.view, 3)
        side = QVBoxLayout(); side.setSpacing(10)
        card = QFrame(); card.setObjectName('card')
        v = QVBoxLayout(card); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(8)
        self.preview_label = QLabel(); self.preview_label.setObjectName('hint'); self.preview_label.setWordWrap(True)
        v.addWidget(self.preview_label)
        nav_box = QWidget(); nav_box.setLayoutDirection(Qt.LeftToRight)
        nav = QHBoxLayout(nav_box); nav.setContentsMargins(0, 0, 0, 0)
        self.prev_btn = QPushButton('‹'); self.next_btn = QPushButton('›')
        self.prev_btn.clicked.connect(lambda: self._show_preview(self.preview_index - 1))
        self.next_btn.clicked.connect(lambda: self._show_preview(self.preview_index + 1))
        self.page_spin = QSpinBox(); self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(lambda v: self._show_preview(v - 1))
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.page_spin, 1)
        nav.addWidget(self.next_btn)
        v.addWidget(nav_box)
        if self.kind == 'pdf':
            self.page_spin.setMaximum(self.page_count)
            v.addWidget(QLabel(tr('Put the signature on')))
            self.where = QComboBox()
            for key, label in (('current', 'This page only'), ('all', 'All pages'), ('first', 'First page'),
                               ('last', 'Last page'), ('custom', 'Pages…')):
                self.where.addItem(tr(label), key)
            self.where.setCurrentIndex(max(0, self.where.findData(self.settings.value('sign/where', 'current'))))
            v.addWidget(self.where)
            self.custom = QLineEdit(); self.custom.setPlaceholderText(tr('e.g. 1-3, 5'))
            self.custom.setLayoutDirection(Qt.LeftToRight)
            v.addWidget(self.custom)
            self.where.currentIndexChanged.connect(self._where_changed)
            self._where_changed()
        else:
            self.page_spin.setMaximum(len(self.paths))
            self.page_spin.hide()
            if len(self.paths) > 1:
                note = QLabel(tr('The same position and size are used on all {n} images.', n=len(self.paths)))
                note.setObjectName('pro'); note.setWordWrap(True)
                v.addWidget(note)
        side.addWidget(card)
        tip = QLabel(tr('Drag the signature to move it. Drag the blue corner to resize it. '
                        'Click anywhere on the page to move it there.'))
        tip.setObjectName('hint'); tip.setWordWrap(True)
        side.addWidget(tip)
        size_row = QHBoxLayout(); size_row.addWidget(QLabel(tr('Size')))
        self.size_slider = QSlider(Qt.Horizontal); self.size_slider.setRange(4, 90)
        self.size_slider.valueChanged.connect(self._size_changed)
        size_row.addWidget(self.size_slider, 1)
        side.addLayout(size_row)
        corners = QHBoxLayout()
        for text, pos in (('↖', (0.05, 0.05)), ('↗', (0.95, 0.05)), ('↙', (0.05, 0.95)), ('↘', (0.95, 0.95)),
                          ('⊙', (0.5, 0.5))):
            b = QPushButton(text); b.setFixedWidth(44)
            b.setToolTip(tr('Snap to this corner'))
            b.clicked.connect(lambda _=False, p=pos: self._snap(*p))
            corners.addWidget(b)
        corners.addStretch(1)
        side.addLayout(corners)
        side.addStretch(1)
        lay.addLayout(side, 2)
        self.view.moved.connect(self._sync_size)
        saved_box = self.settings.value(f'sign/box_{self.kind}')
        try:
            self.view.box = [float(v) for v in saved_box][:3] if saved_box else [0.60, 0.80, 0.28]
        except (TypeError, ValueError):
            pass
        return page

    def _where_changed(self, *_):
        self.custom.setVisible(self.where.currentData() == 'custom')

    def _size_changed(self, value):
        x, y, w = self.view.box
        new = value / 100
        cx = x + w / 2
        self.view.box = [cx - new / 2, y, new]
        self.view._clamp(); self.view.update()

    def _sync_size(self):
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(round(self.view.box[2] * 100)))
        self.size_slider.blockSignals(False)

    def _snap(self, fx, fy):
        pr = self.view._page_rect()
        x, y, w = self.view.box
        h = w * pr.width() * self.view._ratio() / max(1, pr.height())
        margin = 0.04
        nx = margin if fx < 0.3 else (1 - w - margin if fx > 0.7 else 0.5 - w / 2)
        ny = margin if fy < 0.3 else (1 - h - margin if fy > 0.7 else 0.5 - h / 2)
        self.view.box = [nx, ny, w]
        self.view._clamp(); self.view.update()

    def _show_preview(self, index):
        total = self.page_count if self.kind == 'pdf' else len(self.paths)
        index = max(0, min(total - 1, index))
        self.preview_index = index
        self.page_spin.blockSignals(True); self.page_spin.setValue(index + 1); self.page_spin.blockSignals(False)
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setEnabled(index < total - 1)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.kind == 'pdf':
                pix = _pdf_page_pixmap(self.paths[0], index)
                name = Path(self.paths[0]).name
                extra = '' if len(self.paths) == 1 else '  ·  ' + tr('{n} PDF files', n=len(self.paths))
                self.preview_label.setText(f'{name}{extra}\n' + tr('Page {i} of {n}', i=index + 1, n=total))
            else:
                pix = _image_pixmap(self.paths[index])
                self.preview_label.setText(Path(self.paths[index]).name + '\n' +
                                           tr('Image {i} of {n}', i=index + 1, n=total))
        finally:
            QApplication.restoreOverrideCursor()
        self.view.set_page(pix)
        self.prev_btn.setVisible(total > 1); self.next_btn.setVisible(total > 1)

    # ---------------- navigation
    def _go(self, step):
        self.stack.setCurrentIndex(step)
        self.back.setVisible(step == 1)
        if step == 0:
            self.title.setText(tr('Your signature'))
            self.hint.setText(tr('Draw it, upload a picture of it, or pick one you saved before.'))
            self.next.setText(tr('Next'))
        else:
            self.title.setText(tr('Place the signature'))
            self.hint.setText(tr('A new signed copy is saved; the original is not changed.'))
            self.next.setText(tr('Sign'))

    def _next(self):
        if self.stack.currentIndex() == 0:
            path, fresh = self._current_signature()
            if not path or not Path(path).exists():
                QMessageBox.information(self, tr('Signature'), tr('Draw, upload or choose a signature first.'))
                return
            self.signature = Path(path)
            if fresh and self.remember.isChecked():
                keep = signatures_dir() / f'signature_{time.strftime("%Y%m%d_%H%M%S")}_{time.time_ns() % 1000000}.png'
                keep.write_bytes(self.signature.read_bytes())
                self.signature = keep
                self._fill_saved()
            self.settings.setValue('sign/remember', self.remember.isChecked())
            self.settings.setValue('sign/width', self.thick.value())
            self.view.set_signature(self.signature)
            self._go(1)
            self._show_preview(self.preview_index)
            self._sync_size()
        else:
            if self.kind == 'pdf' and self.where.currentData() == 'custom':
                from engine_core import parse_pages
                try:
                    if not parse_pages(self.custom.text(), self.page_count):
                        raise ValueError
                except Exception:
                    QMessageBox.warning(self, tr('Signature'), tr('Write the pages like 1-3, 5'))
                    return
            self.accept()

    def options(self):
        self.settings.setValue(f'sign/box_{self.kind}', [round(v, 4) for v in self.view.box])
        out = {'signature': str(self.signature), 'box': [round(v, 5) for v in self.view.box]}
        if self.kind == 'pdf':
            where = self.where.currentData()
            self.settings.setValue('sign/where', where)
            out['pages'] = self.custom.text().strip() if where == 'custom' else where
            out['page_index'] = self.preview_index
        return out
