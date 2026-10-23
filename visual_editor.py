"""Morphix visual editors: interactive PDF page organizer and image cropper."""
from pathlib import Path
from i18n import tr

import pymupdf as fitz
from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QBrush, QPainter
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QAbstractItemView,
    QDoubleSpinBox, QSlider, QCheckBox)


def pixmap_from_fitz(page, max_side=1200):
    scale = min(max_side / max(page.rect.width, page.rect.height), 2)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
    image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())


class CropCanvas(QGraphicsView):
    crop_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor('#171b25'))
        self.setDragMode(QGraphicsView.NoDrag)
        self._pixmap_item = None
        self._rect_item = None
        self._grid_items = []
        self._start = None
        self._selection = None
        self._handles = []
        self._resize_corner = None
        self.setMinimumSize(360, 270)

    def set_image(self, pixmap):
        self.scene().clear()
        self._pixmap_item = self.scene().addPixmap(pixmap)
        self.scene().setSceneRect(QRectF(pixmap.rect()))
        self._rect_item = None
        self._grid_items = []
        self._selection = None
        self._handles = []
        # Start with a visible crop frame; drag corners, or draw a new box.
        self.set_crop_normalized((0.0, 0.0, 1.0, 1.0))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def set_crop_normalized(self, bounds):
        if not self._pixmap_item or bounds is None:
            return
        scene = self.sceneRect()
        x0, y0, x1, y1 = bounds
        rect = QRectF(scene.width()*x0, scene.height()*y0,
                      scene.width()*(x1-x0), scene.height()*(y1-y0)).normalized()
        if self._rect_item is None:
            self._rect_item = self.scene().addRect(rect, QPen(QColor('#74C4FF'), 2),
                                               QBrush(QColor(74, 164, 244, 25)))
        else:
            self._rect_item.setRect(rect)
        self._selection = rect
        self._paint_guides(rect)

    def _paint_guides(self, rect):
        for line in self._grid_items:
            self.scene().removeItem(line)
        self._grid_items.clear()
        for dot in self._handles:
            self.scene().removeItem(dot)
        self._handles.clear()
        if rect.width() <= 8 or rect.height() <= 8:
            return
        guide_pen = QPen(QColor(220, 240, 255, 165), 1)
        for k in (1,2):
            x=rect.left()+rect.width()*k/3
            y=rect.top()+rect.height()*k/3
            self._grid_items.append(self.scene().addLine(x,rect.top(),x,rect.bottom(),guide_pen))
            self._grid_items.append(self.scene().addLine(rect.left(),y,rect.right(),y,guide_pen))
        for point in (rect.topLeft(),rect.topRight(),rect.bottomRight(),rect.bottomLeft()):
            dot = self.scene().addEllipse(point.x()-5,point.y()-5,10,10,
                      QPen(QColor('#E7F6FF'),1),QBrush(QColor('#3896FF')))
            dot.setZValue(4)
            self._handles.append(dot)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self._pixmap_item:
            super().mousePressEvent(event)
            return
        here = self.mapToScene(event.position().toPoint())
        self._resize_corner = None
        if self._rect_item is not None:
            r = self._rect_item.rect()
            points = (r.topLeft(),r.topRight(),r.bottomRight(),r.bottomLeft())
            radius = max(12.0, self.sceneRect().width()*0.016)
            for i, point in enumerate(points):
                if (here-point).manhattanLength() <= radius*2:
                    self._resize_corner = i
                    self._start = points[(i+2)%4]  # diagonally opposite corner
                    break
        if self._resize_corner is None:
            self._start = here
        if self._rect_item is None:
            self._rect_item = self.scene().addRect(QRectF(),
                QPen(QColor('#74C4FF'),2),QBrush(QColor(74,164,244,25)))
        event.accept()

    def mouseMoveEvent(self, event):
        if self._start is not None and self._rect_item:
            r = (QRectF(self._start, self.mapToScene(event.position().toPoint()))
                 .normalized().intersected(self.sceneRect()))
            self._rect_item.setRect(r)
            self._paint_guides(r)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._start is not None:
            r = self._rect_item.rect()
            self._selection = r if r.width() > 5 and r.height() > 5 else None
            self._start = None
            self._resize_corner = None
            self.crop_changed.emit(self._selection)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def reset_crop(self):
        for line in self._grid_items:
            self.scene().removeItem(line)
        self._grid_items.clear()
        for dot in self._handles:
            self.scene().removeItem(dot)
        self._handles.clear()
        self._selection = None
        if self._rect_item:
            self.scene().removeItem(self._rect_item)
            self._rect_item = None

    def normalized_crop(self):
        if self._selection is None:
            return None
        s = self.sceneRect()
        r = self._selection
        return (max(0, r.left()/s.width()), max(0, r.top()/s.height()),
                min(1, r.right()/s.width()), min(1, r.bottom()/s.height()))


class PdfEditor(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        self.doc = fitz.open(self.path)
        if self.doc.needs_pass:
            self.doc.close()
            raise ValueError(tr('Password-protected PDF is not supported by the visual editor.'))
        self.setWindowTitle(tr('Morphix · PDF Visual Editor'))
        self.resize(1060, 730)
        self.entries = [{'page': i, 'rotation': 0, 'crop': None} for i in range(len(self.doc))]
        root = QVBoxLayout(self)
        root.addWidget(QLabel(tr('Drag pages to reorder · Select a page to preview · Draw a rectangle to crop')))
        body = QHBoxLayout(); root.addLayout(body, 1)
        left = QVBoxLayout(); body.addLayout(left, 1)
        self.list = QListWidget(); self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        left.addWidget(self.list)
        self.canvas = CropCanvas(); body.addWidget(self.canvas, 3)
        tools = QHBoxLayout(); root.addLayout(tools)
        for title, cb in [(tr('Rotate 90°'), self.rotate), (tr('Remove page'), self.remove),
                          (tr('Crop selection'), self.crop), (tr('Reset crop'), self.reset_crop),
                          (tr('Save PDF as…'), self.save_as)]:
            b = QPushButton(title); b.clicked.connect(cb); tools.addWidget(b)
        self.list.currentItemChanged.connect(self.preview)
        for entry in self.entries:
            item = QListWidgetItem(f"Page {entry['page'] + 1}")
            item.setData(Qt.UserRole, entry)
            self.list.addItem(item)
        if self.list.count(): self.list.setCurrentRow(0)

    def current_entry(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def preview(self, current, _previous=None):
        if not current: return
        entry = current.data(Qt.UserRole)
        pix = pixmap_from_fitz(self.doc[entry['page']])
        if entry['rotation']:
            from PySide6.QtGui import QTransform
            pix = pix.transformed(QTransform().rotate(entry['rotation']), Qt.SmoothTransformation)
        self.canvas.set_image(pix)

    def rotate(self):
        e = self.current_entry()
        if e is None: return
        e['rotation'] = (e['rotation'] + 90) % 360
        self.preview(self.list.currentItem())

    def remove(self):
        row = self.list.currentRow()
        if row < 0: return
        if self.list.count() == 1:
            QMessageBox.warning(self, tr('Cannot remove'), tr('A PDF must contain at least one page.'))
            return
        self.list.takeItem(row)
        self.list.setCurrentRow(min(row, self.list.count() - 1))

    def crop(self):
        e = self.current_entry()
        rect = self.canvas.normalized_crop()
        if e is None or rect is None:
            QMessageBox.information(self, tr('Crop'), tr('Drag a rectangle over the page preview first.'))
            return
        # Convert selection from rotated preview coordinates back into unrotated page coordinates.
        x0, y0, x1, y1 = rect
        rot = e['rotation']
        if rot == 90: rect = (y0, 1-x1, y1, 1-x0)
        elif rot == 180: rect = (1-x1, 1-y1, 1-x0, 1-y0)
        elif rot == 270: rect = (1-y1, x0, 1-y0, x1)
        e['crop'] = rect
        self.canvas.reset_crop()
        QMessageBox.information(self, tr('Crop set'), tr('Crop area saved for this page. Click Save PDF as… to export.'))

    def reset_crop(self):
        e = self.current_entry()
        if e is not None: e['crop'] = None
        self.canvas.reset_crop()

    def save_as(self):
        dest, _ = QFileDialog.getSaveFileName(self, tr('Save edited PDF'), str(Path(self.path).with_name(Path(self.path).stem + '_edited.pdf')), 'PDF (*.pdf)')
        if not dest: return
        if Path(dest).resolve() == Path(self.path).resolve():
            QMessageBox.warning(self, tr('Choose a new filename'), tr('Do not overwrite the original PDF.'))
            return
        result = fitz.open()
        try:
            for i in range(self.list.count()):
                e = self.list.item(i).data(Qt.UserRole)
                result.insert_pdf(self.doc, from_page=e['page'], to_page=e['page'])
                p = result[-1]
                if e['crop']:
                    x0, y0, x1, y1 = e['crop']
                    box = p.cropbox
                    p.set_cropbox(fitz.Rect(box.x0 + x0*box.width, box.y0 + y0*box.height,
                                            box.x0 + x1*box.width, box.y0 + y1*box.height))
                p.set_rotation((p.rotation + e['rotation']) % 360)
            result.save(dest, garbage=4, deflate=True)
        except Exception as ex:
            QMessageBox.critical(self, tr('Export failed'), str(ex))
            return
        finally:
            result.close()
        QMessageBox.information(self, tr('Saved'), tr('Created: {path}', path=dest))

    def closeEvent(self, event):
        self.doc.close()
        super().closeEvent(event)


class ImageEditor(QDialog):
    """Visual free-rotation and crop; preserves original, saves to new file."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        with Image.open(self.path) as im:
            self.base_image = ImageOps.exif_transpose(im).copy()
        self.angle = 0.0
        self.preview_base = self.base_image.copy()
        self.preview_base.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
        self._syncing = False
        self.setWindowTitle(tr('Morphix · Crop & Straighten'))
        self.resize(790, 640)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr('Drag the crop corners or draw a new rectangle · Straighten freely · Original is preserved')))
        self.canvas = CropCanvas()
        layout.addWidget(self.canvas, 1)

        controls = QHBoxLayout()
        layout.addLayout(controls)
        for label, angle in [('↶ 90° left', 90), ('↷ 90° right', -90)]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, a=angle: self.set_angle(self.angle + a))
            controls.addWidget(button)
        controls.addWidget(QLabel(tr('Angle')))
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(-450, 450)
        self.angle_slider.setValue(0)
        self.angle_slider.valueChanged.connect(lambda v: self.set_angle(v / 10))
        controls.addWidget(self.angle_slider, 1)
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-180, 180)
        self.angle_spin.setDecimals(1)
        self.angle_spin.setSingleStep(.5)
        self.angle_spin.setSuffix('°')
        self.angle_spin.valueChanged.connect(self.set_angle)
        controls.addWidget(self.angle_spin)
        reset = QPushButton(tr('Reset'))
        reset.clicked.connect(lambda: self.set_angle(0))
        controls.addWidget(reset)

        bottom = QHBoxLayout()
        layout.addLayout(bottom)
        self.crop_enabled = QCheckBox(tr('Crop to selected rectangle'))
        self.crop_enabled.setChecked(True)
        bottom.addWidget(self.crop_enabled)
        reset_crop = QPushButton(tr('Clear crop'))
        reset_crop.clicked.connect(self.canvas.reset_crop)
        bottom.addWidget(reset_crop)
        bottom.addStretch()
        save = QPushButton(tr('Save edited image as…'))
        save.clicked.connect(self.save_as)
        bottom.addWidget(save)
        self.setStyleSheet('''QDialog{background:#0A172B;color:#E7F4FF;}
          QLabel,QCheckBox{color:#DBEAFF;} QPushButton{background:#153658;color:#F0F7FF;
          border:1px solid #406B9B;padding:9px;border-radius:8px;}
          QPushButton:hover{background:#245483;}
          QDoubleSpinBox{color:#F4F9FF;background:#183450;padding:6px;border-radius:6px;}''')
        self.refresh()

    def _rotated(self, preview=False):
        from image_tools import rotate_image
        base = self.preview_base if preview else self.base_image
        return rotate_image(base, self.angle)

    def set_angle(self, value):
        if self._syncing:
            return
        value = max(-180., min(180., float(value)))
        self.angle = value
        self._syncing = True
        self.angle_spin.setValue(value)
        self.angle_slider.setValue(round(max(-45.,min(45.,value))*10))
        self._syncing = False
        self.refresh()

    def refresh(self):
        previous_crop = self.canvas.normalized_crop() if self.canvas._pixmap_item else None
        preview = self._rotated(preview=True)
        if preview.mode not in ('RGB','RGBA'):
            preview = preview.convert('RGBA')
        raw = preview.tobytes()
        fmt = QImage.Format_RGB888 if preview.mode == 'RGB' else QImage.Format_RGBA8888
        self.canvas.set_image(QPixmap.fromImage(QImage(raw, preview.width, preview.height,
                           len(raw)//preview.height, fmt).copy()))
        if previous_crop:
            self.canvas.set_crop_normalized(previous_crop)

    def _write_image(self, destination):
        from image_tools import export_image_edit
        rect = self.canvas.normalized_crop() if self.crop_enabled.isChecked() else None
        return export_image_edit(self.base_image, destination, angle=self.angle,
                                 crop=rect, original_path=self.path)

    def save_as(self):
        dest, _ = QFileDialog.getSaveFileName(self, tr('Save edited image'),
            str(Path(self.path).with_name(Path(self.path).stem+'_edited.png')),
            'Images (*.png *.jpg *.jpeg *.webp)')
        if not dest:
            return
        try:
            output = self._write_image(dest)
            QMessageBox.information(self, tr('Saved'), tr('Created: {path}', path=output))
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, tr('Export failed'), str(exc))


class QuickImageEditor(ImageEditor):
    """Fast image crop/straighten popup — opens without Morphix Studio."""
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        self.setWindowTitle(tr('Morphix · Quick Crop & Rotate'))
        self.resize(730, 610)
        self.setMinimumSize(570, 490)
        lower = self.layout().itemAt(self.layout().count()-1).layout()
        quick = QPushButton(tr('Save Copy'))
        quick.setToolTip(tr('Save alongside the original without overwriting it'))
        quick.clicked.connect(self.save_copy)
        lower.insertWidget(lower.count()-1, quick)
        cancel = QPushButton(tr('Cancel'))
        cancel.clicked.connect(self.reject)
        lower.addWidget(cancel)

    def save_copy(self):
        base = Path(self.path)
        suffix = base.suffix.lower() if base.suffix.lower() in ('.png','.jpg','.jpeg','.webp') else '.png'
        candidate = base.with_name(base.stem + '_edited' + suffix)
        i = 2
        while candidate.exists():
            candidate = base.with_name(f'{base.stem}_edited_{i}{suffix}')
            i += 1
        try:
            output = self._write_image(candidate)
            print(f'[Morphix] Quick edit saved: {output}', flush=True)
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, tr('Export failed'), str(exc))
