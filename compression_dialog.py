"""Small glass-blue compression popover shown from the wheel or Studio."""
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout,
                               QComboBox, QSlider, QCheckBox, QPushButton)
from compression_engine import image_quality, RASTER_FROM
from i18n import tr, option_row, slider_css


def nice_size(size):
    value = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{value:.1f} {unit}' if unit != 'B' else f'{int(value)} B'
        value /= 1024


class CompressionDialog(QDialog):
    PRESETS = (
        ('Light · Best quality', 15),
        ('Balanced · Recommended', 45),
        ('Strong · Much smaller', 75),
        ('Maximum · Very small (quality drops)', 92),
        ('Extreme · Smallest possible', 100),
        ('Custom', None),
    )

    def __init__(self, paths, kind='image', parent=None):
        super().__init__(parent)
        self.paths = [str(p) for p in paths]
        self.kind = kind
        self.setWindowTitle(tr('Morphix · Compression'))
        self.setMinimumWidth(440)
        self.setModal(True)
        self.setStyleSheet('''
            QDialog { background: #0A1B31; color: #EBF5FF; }
            QLabel { color: #DCEBFA; background: transparent; }
            QLabel#muted { color: #91B3D5; }
            QLabel#big { font-size: 16px; font-weight: 750; color: #ACD9FF; }
            QComboBox { border: 1px solid #426D9E; border-radius: 9px;
                        padding: 9px; color: #EAF5FF; background: #193351; }
            QComboBox QAbstractItemView { background: #122940; color: #EAF5FF; }
            QPushButton { border: 1px solid #426D9E; border-radius: 9px;
                          padding: 10px 14px; background: #17314E; color: white; }
            QPushButton#primary { background: #2379D9; border-color: #66B4FF; font-weight: 700; }
            QCheckBox { color: #DCEBFA; }
            QWidget#optionRow { background: transparent; }
            QLabel#optionLabel { color: #DCEBFA; }
        ''' + slider_css('#294666', '#4EA4FF', '#C0E2FF'))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(21, 18, 21, 18)
        layout.setSpacing(12)
        title = QLabel(tr('Compression'))
        title.setObjectName('big')
        layout.addWidget(title)
        layout.addWidget(QLabel(tr('{n} file(s)', n=len(self.paths)) + ' · ' + ('PDF' if kind=='pdf' else tr('Images'))))
        total_size = sum(Path(p).stat().st_size for p in self.paths if Path(p).exists())
        self.source_label = QLabel(tr('Original size:') + ' ' + nice_size(total_size))
        self.source_label.setObjectName('muted')
        layout.addWidget(self.source_label)
        self.preset = QComboBox()
        for label, value in self.PRESETS:
            self.preset.addItem(tr(label), userData=value)
        layout.addWidget(self.preset)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Compression strength')))
        self.strength_label = QLabel('')
        row.addStretch()
        row.addWidget(self.strength_label)
        layout.addLayout(row)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        layout.addWidget(self.slider)
        self.resize_box = QCheckBox()
        self.resize_box.setChecked(False)
        if kind == 'image':
            layout.addWidget(option_row(self.resize_box, tr('Also reduce image dimensions for a smaller file')))
        self.gray_box = QCheckBox()
        self.gray_box.setChecked(bool(QSettings('Morphix', 'Morphix').value('compression_gray_pdf', False, type=bool)))
        if kind == 'pdf':
            layout.addWidget(option_row(self.gray_box, tr('Black & white (smaller, good for text documents)')))
            self.gray_box.toggled.connect(self._update_info)
        self.info = QLabel('')
        self.info.setWordWrap(True)
        self.info.setObjectName('muted')
        layout.addWidget(self.info)
        self.preview = QLabel('')
        self.preview.setObjectName('muted')
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        buttons = QHBoxLayout()
        cancel = QPushButton(tr('Cancel'))
        confirm = QPushButton(tr('Compress'))
        confirm.setObjectName('primary')
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self._accept)
        self.preset.currentIndexChanged.connect(self._preset_changed)
        self.slider.valueChanged.connect(self._slider_changed)
        self.resize_box.toggled.connect(self._update_info)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(190)
        self.timer.timeout.connect(self._estimate_first_image)
        saved = QSettings('Morphix', 'Morphix').value(f'compression_strength_{kind}', 45)
        try: saved = max(0, min(100, int(saved)))
        except (TypeError, ValueError): saved = 45
        self.slider.setValue(saved)
        idx = next((i for i, (_, v) in enumerate(self.PRESETS) if v == saved), len(self.PRESETS) - 1)
        self.preset.setCurrentIndex(idx)
        self._update_info()

    def _accept(self):
        QSettings('Morphix', 'Morphix').setValue(f'compression_strength_{self.kind}', self.slider.value())
        QSettings('Morphix', 'Morphix').setValue('compression_gray_pdf', self.gray_box.isChecked())
        self.accept()

    def _preset_changed(self, index):
        val = self.preset.itemData(index)
        if val is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(val)
            self.slider.blockSignals(False)
            self._update_info()

    def _slider_changed(self, value):
        if self.preset.currentData() != value:
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(len(self.PRESETS)-1)
            self.preset.blockSignals(False)
        self._update_info()

    def _update_info(self):
        strength = self.slider.value()
        self.strength_label.setText(f'{strength}%')
        if self.kind == 'image':
            self.info.setText(tr('Saved as JPEG at quality {q}/95. Stronger levels look softer; '
                                 'transparent areas become white. Your original is never changed.',
                                 q=image_quality(strength)))
            self.timer.start()
        else:
            if strength >= RASTER_FROM:
                self.info.setText(tr('Extreme: every page is redrawn as a compressed image. The file becomes '
                                     'much smaller, but text can no longer be selected or searched — '
                                     'run OCR on the result if you need that. Your original is never changed.'))
            elif strength >= 30:
                self.info.setText(tr('Images inside the PDF are reduced; text stays sharp and selectable. '
                                     'For an even smaller file, move the slider to the far end. '
                                     'Your original is never changed.'))
            else:
                self.info.setText(tr('Lossless clean-up only: nothing visible changes. '
                                     'Your original is never changed.'))
            self.preview.setText(tr('The final size is shown when the file is saved.'))

    def _estimate_first_image(self):
        if self.kind != 'image' or not self.paths:
            return
        try:
            from PIL import Image, ImageOps
            from io import BytesIO
            from compression_engine import save_image_compressed
            first = Path(self.paths[0])
            with Image.open(first) as original:
                if original.width * original.height > 12_000_000:
                    self.preview.setText(tr('Large image — the exact size appears after saving.'))
                    return
                im = ImageOps.exif_transpose(original)
                stream = BytesIO()
                save_image_compressed(im, stream, quality=image_quality(self.slider.value()),
                                      resize_max=self._resize_max())
                est = stream.tell()
            self.preview.setText(tr('First image:') + ' ' + nice_size(first.stat().st_size)
                                 + ' → ~' + nice_size(est))
        except Exception:
            self.preview.setText(tr('No preview for this image.'))

    def _resize_max(self):
        if self.kind != 'image' or not self.resize_box.isChecked():
            return None
        return max(800, round(3200 - self.slider.value() * 24))

    def options(self):
        strength = self.slider.value()
        result = {'compression_strength': strength}
        if self.kind == 'pdf':
            result['pdf_grayscale'] = self.gray_box.isChecked()
        if self.kind == 'image':
            result['quality'] = image_quality(strength)
            if self._resize_max() is not None:
                result['resize_max'] = self._resize_max()
        return result
