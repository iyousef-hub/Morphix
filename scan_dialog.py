"""Scanner window (Morphix 1.10): pages from photos, corners, looks and the finished document."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QSettings, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap, QBrush
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog,
                               QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from i18n import tr, amp

IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.heic', '.heif')

STYLE = """
QDialog { background:#0B1A2E; color:#EAF4FF; }
QLabel { color:#DCEBFC; background:transparent; }
QLabel#title { font-size:19px; font-weight:800; color:#FFFFFF; }
QLabel#hint { color:#93B2D3; font-size:12px; }
QLabel#section { color:#7FB4EE; font-size:11px; font-weight:800; letter-spacing:1px; }
QFrame#card { background:#112440; border:1px solid #284A70; border-radius:12px; }
QComboBox, QLineEdit { background:#152C49; border:1px solid #31597F; border-radius:8px; padding:6px 10px; color:#EAF4FF; }
QPushButton { color:#EAF4FF; background:#1A3555; border:1px solid #31597F; border-radius:9px; padding:7px 12px; font-weight:600; }
QPushButton:hover { background:#24496F; }
QPushButton:disabled { color:#6F89AA; }
QPushButton#primary { background:#247FE4; border-color:#55A3FB; color:white; padding:8px 18px; }
QPushButton#look { padding:9px 10px; text-align:left; }
QPushButton#look:checked, QPushButton#mode:checked { background:#24518A; border:2px solid #4F9FF9; }
QPushButton#mode { padding:6px 14px; }
QListWidget { background:#0E1F36; border:1px solid #284A70; border-radius:12px; padding:6px; color:#DCEBFC; outline:none; }
QListWidget::item { border-radius:8px; padding:4px; margin:2px; }
QListWidget::item:selected { background:#24518A; }
QCheckBox { color:#DCEBFC; spacing:8px; }
"""

LOOKS = (('enhanced', 'Enhanced — recommended', 'Clean white paper, no shadows, colours kept.'),
         ('original', 'Original colours', 'Straightened only, exactly as photographed.'),
         ('gray', 'Grayscale', 'Even grey tones — good for printing.'),
         ('bw', 'Black & white', 'Sharp black text on pure white — the smallest file.'))


def np_to_qimage(arr):
    import numpy as np
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        h, w = arr.shape
        return QImage(arr.data, w, h, w, QImage.Format_Grayscale8).copy()
    h, w, _ = arr.shape
    return QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()


# ===================================================================== corners
class CornerEditor(QWidget):
    """The photo with the sheet's outline; drag a corner (a magnifier helps)."""
    changed = Signal()
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        self.setMouseTracking(True)
        self.image = None           # QImage of the (preview-size) photo
        self.corners = None         # 4 × [x, y] in 0..1
        self.drag = -1
        self.hover = -1

    def set_page(self, image, corners):
        self.image = image
        self.corners = [list(c) for c in corners] if corners else None
        self.drag = -1
        self.update()

    def _frame(self):
        if self.image is None or self.image.isNull():
            return QRectF()
        pad = 26
        avail = QRectF(self.rect()).adjusted(pad, pad, -pad, -pad)
        s = min(avail.width() / self.image.width(), avail.height() / self.image.height())
        w, h = self.image.width() * s, self.image.height() * s
        return QRectF(avail.center().x() - w / 2, avail.center().y() - h / 2, w, h)

    def _pt(self, i, frame=None):
        f = frame or self._frame()
        x, y = self.corners[i]
        return QPointF(f.left() + x * f.width(), f.top() + y * f.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#081426'))
        f = self._frame()
        if f.isNull():
            p.setPen(QColor('#7F9BC0'))
            p.drawText(self.rect(), Qt.AlignCenter, tr('Add photos of your documents to start.'))
            return
        p.drawImage(f, self.image)
        if not self.corners:
            return
        pts = [self._pt(i, f) for i in range(4)]
        outside = QPainterPath(); outside.addRect(f)
        inside = QPainterPath(); inside.moveTo(pts[0])
        for q in pts[1:]:
            inside.lineTo(q)
        inside.closeSubpath()
        p.fillPath(outside.subtracted(inside), QColor(4, 10, 22, 150))
        p.setPen(QPen(QColor('#4FA3FF'), 2.4))
        p.setBrush(QColor(79, 163, 255, 28))
        p.drawPath(inside)
        for i, q in enumerate(pts):
            r = 11 if i in (self.drag, self.hover) else 9
            p.setPen(QPen(QColor('#FFFFFF'), 2.5))
            p.setBrush(QColor('#2F8CF5'))
            p.drawEllipse(q, r, r)
        if self.drag >= 0:
            self._loupe(p, f, pts[self.drag])

    def _loupe(self, p, f, at):
        """Magnified view under the finger/pointer, so the corner lands exactly on the paper's tip."""
        size, zoom = 120, 3.0
        cx = (at.x() - f.left()) / f.width() * self.image.width()
        cy = (at.y() - f.top()) / f.height() * self.image.height()
        src_w = size / zoom * self.image.width() / f.width()
        src = QRectF(cx - src_w / 2, cy - src_w / 2, src_w, src_w)
        box = QRectF(at.x() - size / 2, at.y() - size - 34, size, size)
        if box.top() < 4:
            box.moveTop(at.y() + 34)
        box.moveLeft(min(max(4, box.left()), self.width() - size - 4))
        clip = QPainterPath(); clip.addEllipse(box)
        p.save()
        p.setClipPath(clip)
        p.fillRect(box, QColor('#081426'))
        p.drawImage(box, self.image, src)
        p.restore()
        p.setPen(QPen(QColor('#FFFFFF'), 3)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(box)
        c = box.center()
        p.setPen(QPen(QColor('#4FA3FF'), 1.5))
        p.drawLine(QPointF(c.x() - 10, c.y()), QPointF(c.x() + 10, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 10), QPointF(c.x(), c.y() + 10))

    def _nearest(self, pos):
        if not self.corners:
            return -1
        f = self._frame()
        best, dist = -1, 30.0
        for i in range(4):
            d = (self._pt(i, f) - QPointF(pos)).manhattanLength()
            if d < dist:
                best, dist = i, d
        return best

    def mousePressEvent(self, e):
        self.drag = self._nearest(e.position())
        self.update()

    def mouseMoveEvent(self, e):
        if self.drag < 0:
            h = self._nearest(e.position())
            if h != self.hover:
                self.hover = h
                self.setCursor(Qt.OpenHandCursor if h >= 0 else Qt.ArrowCursor)
                self.update()
            return
        f = self._frame()
        x = min(1.0, max(0.0, (e.position().x() - f.left()) / f.width()))
        y = min(1.0, max(0.0, (e.position().y() - f.top()) / f.height()))
        self.corners[self.drag] = [x, y]
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, _):
        if self.drag >= 0:
            self.drag = -1
            self.update()
            self.finished.emit()


class ResultView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None

    def set_image(self, image):
        self.image = image
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor('#081426'))
        if self.image is None:
            return
        pad = 26
        avail = QRectF(self.rect()).adjusted(pad, pad, -pad, -pad)
        s = min(avail.width() / self.image.width(), avail.height() / self.image.height())
        w, h = self.image.width() * s, self.image.height() * s
        r = QRectF(avail.center().x() - w / 2, avail.center().y() - h / 2, w, h)
        p.fillRect(r.adjusted(4, 6, 4, 6), QColor(0, 0, 0, 90))
        p.drawImage(r, self.image)


# ===================================================================== window
class ScanDialog(QDialog):
    def __init__(self, paths=(), parent=None):
        super().__init__(parent)
        import scan_engine
        self.engine = scan_engine
        self.settings = QSettings('Morphix', 'Morphix')
        self.setWindowTitle(tr('Morphix · Scan documents'))
        self.setStyleSheet(STYLE)
        self.resize(1240, 800)
        self.setMinimumSize(980, 640)
        self.pages = []             # dicts: id, path, corners, rotation, filter, found
        self._next_id = 0
        self.cache = {}             # path → preview numpy image
        self.current = -1
        self._pending = []
        self._detect_timer = QTimer(self, interval=0, timeout=self._detect_next)
        self._preview_timer = QTimer(self, singleShot=True, interval=90, timeout=self._refresh_result)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(10)
        title = QLabel(tr('Scan documents')); title.setObjectName('title')
        hint = QLabel(tr('Photos of paper become clean, straight pages. Morphix finds each sheet\'s corners — '
                         'drag a corner to fix it. Everything stays on this computer.'))
        hint.setObjectName('hint'); hint.setWordWrap(True)
        root.addWidget(title); root.addWidget(hint)

        body = QHBoxLayout(); body.setSpacing(14)
        root.addLayout(body, 1)

        # ---------------- pages
        left = QVBoxLayout(); left.setSpacing(8)
        lab = QLabel(tr('PAGES')); lab.setObjectName('section'); left.addWidget(lab)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setFlow(QListWidget.TopToBottom)
        self.list.setWrapping(False)
        self.list.setIconSize(QSize(140, 180))
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setMovement(QListWidget.Snap)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setSpacing(4)
        self.list.setFixedWidth(200)
        self.list.currentRowChanged.connect(self._select)
        self.list.model().rowsMoved.connect(self._reordered)
        left.addWidget(self.list, 1)
        add = QPushButton('＋  ' + tr('Add photos')); add.clicked.connect(self._add_photos)
        phone = QPushButton('📱  ' + tr('From my phone')); phone.clicked.connect(self._from_phone)
        left.addWidget(add); left.addWidget(phone)
        body.addLayout(left)

        # ---------------- editor
        mid = QVBoxLayout(); mid.setSpacing(8)
        modes = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        for i, text in enumerate((tr('Adjust corners'), tr('Result'))):
            b = QPushButton(text); b.setObjectName('mode'); b.setCheckable(True)
            self.mode_group.addButton(b, i); modes.addWidget(b)
        self.mode_group.button(1).setChecked(True)
        self.mode_group.idClicked.connect(self._mode)
        modes.addStretch()
        self.page_label = QLabel(''); self.page_label.setObjectName('hint')
        modes.addWidget(self.page_label)
        mid.addLayout(modes)
        self.stack = QStackedWidget()
        self.editor = CornerEditor()
        self.result = ResultView()
        self.stack.addWidget(self.editor); self.stack.addWidget(self.result)
        self.stack.setCurrentIndex(1)
        self.editor.changed.connect(lambda: self._preview_timer.start())
        self.editor.finished.connect(self._corners_done)
        mid.addWidget(self.stack, 1)
        tools = QHBoxLayout()
        self.btn_auto = QPushButton('✦  ' + tr('Find edges')); self.btn_auto.clicked.connect(self._auto)
        self.btn_full = QPushButton('▢  ' + tr('Whole photo')); self.btn_full.clicked.connect(self._whole)
        self.btn_left = QPushButton('⟲'); self.btn_left.clicked.connect(lambda: self._rotate(-90))
        self.btn_right = QPushButton('⟳'); self.btn_right.clicked.connect(lambda: self._rotate(90))
        self.btn_del = QPushButton('🗑  ' + tr('Remove page')); self.btn_del.clicked.connect(self._delete)
        for b in (self.btn_auto, self.btn_full, self.btn_left, self.btn_right):
            tools.addWidget(b)
        tools.addStretch(); tools.addWidget(self.btn_del)
        mid.addLayout(tools)
        body.addLayout(mid, 1)

        # ---------------- options
        side = QFrame(); side.setObjectName('card'); side.setFixedWidth(300)
        opts = QVBoxLayout(side); opts.setContentsMargins(14, 14, 14, 14); opts.setSpacing(8)
        lab = QLabel(tr('LOOK')); lab.setObjectName('section'); opts.addWidget(lab)
        self.look_group = QButtonGroup(self)
        for key, text, about in LOOKS:
            b = QPushButton(amp(tr(text))); b.setObjectName('look'); b.setCheckable(True)
            b.setProperty('key', key); b.setToolTip(tr(about))
            self.look_group.addButton(b)
            opts.addWidget(b)
        self.look_group.buttonClicked.connect(self._look)
        self.look_about = QLabel(''); self.look_about.setObjectName('hint'); self.look_about.setWordWrap(True)
        opts.addWidget(self.look_about)
        self.all_pages = QCheckBox(tr('Use this look for every page'))
        self.all_pages.setChecked(True)
        opts.addWidget(self.all_pages)
        opts.addSpacing(8)
        lab = QLabel(tr('DOCUMENT')); lab.setObjectName('section'); opts.addWidget(lab)
        self.name = QLineEdit(tr('Scan') + ' ' + datetime.now().strftime('%Y-%m-%d %H.%M'))
        opts.addWidget(QLabel(tr('File name'))); opts.addWidget(self.name)
        self.size = QComboBox()
        for key, text in (('a4', 'A4'), ('letter', 'Letter'), ('fit', tr('Same shape as the photo'))):
            self.size.addItem(text, key)
        self.size.setCurrentIndex(max(0, self.size.findData(self.settings.value('scan/size', 'a4'))))
        opts.addWidget(QLabel(tr('Page size'))); opts.addWidget(self.size)
        self.quality = QComboBox()
        for key, text in (('high', 'High — for printing'), ('balanced', 'Balanced — recommended'),
                          ('small', 'Small — for email and online forms')):
            self.quality.addItem(tr(text), key)
        self.quality.setCurrentIndex(max(0, self.quality.findData(self.settings.value('scan/quality', 'balanced'))))
        opts.addWidget(QLabel(tr('Quality'))); opts.addWidget(self.quality)
        self.output = QComboBox()
        self.output.addItem(tr('One PDF'), 'pdf')
        self.output.addItem(tr('Pictures (one per page)'), 'images')
        opts.addWidget(QLabel(tr('Save as'))); opts.addWidget(self.output)
        opts.addSpacing(4)
        self.ocr = QCheckBox(tr('Searchable text (Arabic + English)'))
        self.ocr.setChecked(self.settings.value('scan/ocr', True, type=bool))
        self.id_card = QCheckBox(tr('ID card: both sides on one page'))
        self.id_card.setToolTip(tr('Pages 1 and 2 go on one sheet at the real card size — ready to print.'))
        opts.addWidget(self.ocr); opts.addWidget(self.id_card)
        self.output.currentIndexChanged.connect(self._output_changed)
        opts.addStretch()
        body.addWidget(side)

        # ---------------- footer
        foot = QHBoxLayout()
        self.summary = QLabel(''); self.summary.setObjectName('hint')
        foot.addWidget(self.summary, 1)
        cancel = QPushButton(tr('Cancel')); cancel.clicked.connect(self.reject)
        self.save = QPushButton(tr('Save the scan')); self.save.setObjectName('primary')
        self.save.clicked.connect(self._accept)
        foot.addWidget(cancel); foot.addWidget(self.save)
        root.addLayout(foot)

        self.add_paths(paths)
        self._sync_buttons()

    # ------------------------------------------------------------- pages
    def add_paths(self, paths):
        default_look = str(self.settings.value('scan/look', 'enhanced'))
        if default_look not in self.engine.FILTERS:
            default_look = 'enhanced'
        look = self.pages[self.current]['filter'] if 0 <= self.current < len(self.pages) else default_look
        first_new = len(self.pages)
        for path in paths:
            if not str(path).lower().endswith(IMAGE_EXT) or not Path(path).is_file():
                continue
            self._next_id += 1
            page = {'id': self._next_id, 'path': str(path), 'corners': self.engine.full_corners(), 'rotation': 0,
                    'filter': look, 'found': None}
            self.pages.append(page)
            item = QListWidgetItem(f'{len(self.pages)}')
            item.setData(Qt.UserRole, page['id'])
            item.setTextAlignment(Qt.AlignHCenter)
            self.list.addItem(item)
            self._pending.append(page)
            self._update_thumb(page)
        if self._pending:
            self._detect_timer.start()
        if first_new < len(self.pages):
            self.list.setCurrentRow(first_new)
        self._sync_buttons()

    def _preview_source(self, path):
        arr = self.cache.get(path)
        if arr is None:
            arr = self.engine.load_rgb(path, max_side=1600)
            self.cache[path] = arr
        return arr

    def _detect_next(self):
        """Find each sheet in the background of the event loop, one photo at a time."""
        while self._pending:
            page = self._pending.pop(0)
            if page not in self.pages:
                continue
            try:
                corners, found = self.engine.find_document(self._preview_source(page['path']))
            except Exception:
                corners, found = self.engine.full_corners(), False
            page['corners'], page['found'] = corners, found
            self._update_thumb(page)
            if self.current >= 0 and self.pages[self.current] is page:
                self._select(self.current)
            return
        self._detect_timer.stop()
        self._sync_buttons()

    def _render(self, page, max_side=900):
        src = self._preview_source(page['path'])
        flat = self.engine.flatten(src, page['corners'], max_side=max_side)
        flat = self.engine.rotate(flat, page['rotation'])
        return np_to_qimage(self.engine.apply_filter(flat, page['filter']))

    def _update_thumb(self, page):
        row = self.pages.index(page)
        item = self._item_for(page)
        if item is None:
            return
        try:
            img = self._render(page, max_side=420)
            pix = QPixmap.fromImage(img).scaled(140, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(pix))
        except Exception as exc:
            print(f'[Morphix] Scan preview failed: {exc}', flush=True)
        item.setText(str(row + 1))

    def _item_for(self, page):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == page['id']:
                return self.list.item(i)
        return None

    def _reordered(self, *_):
        by_id = {p['id']: p for p in self.pages}
        self.pages = [by_id[self.list.item(i).data(Qt.UserRole)] for i in range(self.list.count())]
        for i in range(self.list.count()):
            self.list.item(i).setText(str(i + 1))
        self.current = self.list.currentRow()
        self._sync_buttons()

    def _select(self, row):
        self.current = row
        if not 0 <= row < len(self.pages):
            self.editor.set_page(None, None)
            self.result.set_image(None)
            self._sync_buttons()
            return
        page = self.pages[row]
        src = self._preview_source(page['path'])
        self.editor.set_page(np_to_qimage(src), page['corners'])
        for b in self.look_group.buttons():
            b.setChecked(b.property('key') == page['filter'])
        self._about_look(page['filter'])
        self._refresh_result()
        self._sync_buttons()

    def _refresh_result(self):
        if not 0 <= self.current < len(self.pages):
            return
        page = self.pages[self.current]
        if self.editor.corners:
            page['corners'] = [list(c) for c in self.editor.corners]
        try:
            self.result.set_image(self._render(page, max_side=1100))
        except Exception as exc:
            print(f'[Morphix] Scan preview failed: {exc}', flush=True)

    def _corners_done(self):
        self._refresh_result()
        self._update_thumb(self.pages[self.current])

    def _mode(self, index):
        self.stack.setCurrentIndex(index)

    def _auto(self):
        if 0 <= self.current < len(self.pages):
            page = self.pages[self.current]
            page['corners'], page['found'] = self.engine.find_document(self._preview_source(page['path']))
            if not page['found']:
                QMessageBox.information(self, tr('Scan documents'),
                                        tr('No clear sheet edges were found in this photo, so the whole photo is '
                                           'used. Drag the corners to the paper\'s tips.'))
            self._select(self.current)
            self._update_thumb(page)

    def _whole(self):
        if 0 <= self.current < len(self.pages):
            page = self.pages[self.current]
            page['corners'] = self.engine.full_corners()
            self._select(self.current)
            self._update_thumb(page)

    def _rotate(self, deg):
        if 0 <= self.current < len(self.pages):
            page = self.pages[self.current]
            page['rotation'] = (page['rotation'] + deg) % 360
            self._refresh_result()
            self._update_thumb(page)

    def _delete(self):
        if not 0 <= self.current < len(self.pages):
            return
        page = self.pages.pop(self.current)
        if page in self._pending:
            self._pending.remove(page)
        self.list.takeItem(self.current)
        for i in range(self.list.count()):
            self.list.item(i).setText(str(i + 1))
        self._select(self.list.currentRow())

    def _look(self, button):
        key = button.property('key')
        targets = self.pages if self.all_pages.isChecked() else (
            [self.pages[self.current]] if 0 <= self.current < len(self.pages) else [])
        for page in targets:
            page['filter'] = key
            self._update_thumb(page)
        self.settings.setValue('scan/look', key)
        self._about_look(key)
        self._refresh_result()

    def _about_look(self, key):
        self.look_about.setText(next((tr(a) for k, _, a in LOOKS if k == key), ''))

    def _output_changed(self):
        pdf = self.output.currentData() == 'pdf'
        for w in (self.ocr, self.id_card, self.size):
            w.setEnabled(pdf)

    def _add_photos(self):
        start = self.settings.value('scan/last_folder', str(Path.home()))
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Choose photos of your documents'), start,
                                                tr('Pictures') + ' (*.jpg *.jpeg *.png *.webp *.heic *.heif *.bmp *.tif *.tiff)')
        if paths:
            self.settings.setValue('scan/last_folder', str(Path(paths[0]).parent))
            self.add_paths(paths)

    def _from_phone(self):
        from phone_transfer import PhoneDialog
        dialog = PhoneDialog(self, purpose='scan')
        dialog.exec()
        received = [p for p in dialog.received_paths() if p.lower().endswith(IMAGE_EXT)]
        if received:
            self.add_paths(received)

    def _sync_buttons(self):
        has = 0 <= self.current < len(self.pages)
        for b in (self.btn_auto, self.btn_full, self.btn_left, self.btn_right, self.btn_del):
            b.setEnabled(has)
        self.save.setEnabled(bool(self.pages))
        n = len(self.pages)
        self.page_label.setText(tr('Page {i} of {n}', i=self.current + 1, n=n) if has else '')
        waiting = len(self._pending)
        self.summary.setText(tr('Finding the edges… {n} left', n=waiting) if waiting else
                             tr('{n} page(s)', n=n) if n else tr('Add photos of your documents to start.'))

    # ------------------------------------------------------------- result
    def _accept(self):
        if not self.pages:
            return
        if self.id_card.isChecked() and self.output.currentData() == 'pdf' and len(self.pages) % 2:
            QMessageBox.information(self, tr('Scan documents'),
                                    tr('ID card layout puts two photos (front and back) on each page. '
                                       'The last page will have one side only.'))
        self.settings.setValue('scan/size', self.size.currentData())
        self.settings.setValue('scan/quality', self.quality.currentData())
        self.settings.setValue('scan/ocr', self.ocr.isChecked())
        self.accept()

    def options(self):
        return {
            'scan_pages': [{'path': p['path'], 'corners': p['corners'], 'rotation': p['rotation'],
                            'filter': p['filter']} for p in self.pages],
            'scan_name': self.name.text().strip() or tr('Scan'),
            'page_size': self.size.currentData(),
            'scan_quality': self.quality.currentData(),
            'scan_ocr': self.ocr.isChecked() and self.output.currentData() == 'pdf',
            'id_card': self.id_card.isChecked() and self.output.currentData() == 'pdf',
            'scan_output': self.output.currentData(),
        }
