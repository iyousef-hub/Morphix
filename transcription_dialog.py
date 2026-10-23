"""Options dialog for Speech → Text, including the one-time model download."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QProgressBar, QMessageBox, QDialogButtonBox, QFrame)

import transcription_engine as te
from i18n import tr, option_row

STYLE = """
QDialog { background:#0B1A2E; color:#EAF4FF; }
QLabel { color:#DCEBFC; background:transparent; }
QLabel#title { font-size:19px; font-weight:800; color:#FFFFFF; }
QLabel#hint { color:#93B2D3; font-size:12px; }
QLabel#ok { color:#8FF0D7; font-weight:700; }
QLabel#warn { color:#FFD27A; font-weight:700; }
QComboBox, QCheckBox { color:#EAF4FF; font-size:13px; }
QComboBox { background:#152C49; border:1px solid #31597F; border-radius:8px; padding:6px 10px; }
QFrame#card { background:#112440; border:1px solid #284A70; border-radius:12px; }
QPushButton { color:#EAF4FF; background:#1A3555; border:1px solid #31597F; border-radius:9px; padding:9px 14px; font-weight:600; }
QPushButton:hover { background:#24496F; }
QPushButton#primary { background:#247FE4; border-color:#55A3FB; color:white; }
QProgressBar { background:#24384F; border:0; border-radius:4px; height:8px; }
QProgressBar::chunk { background:#459EFC; border-radius:4px; }
"""


def _human_duration(paths):
    total = 0.0
    try:
        import subprocess, re
        ff = te._ffmpeg()
        for p in paths[:50]:
            out = subprocess.run([ff, '-hide_banner', '-i', str(p)], capture_output=True,
                                 text=True, errors='replace', timeout=15).stderr
            m = re.search(r'Duration:\s*(\d+):(\d+):(\d+)', out)
            if m:
                total += int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
    except Exception:
        return ''
    if not total:
        return ''
    h, m = divmod(int(total) // 60, 60)
    return f'{h} h {m} min' if h else f'{m} min'


class TranscriptionDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = list(paths)
        self.settings = QSettings('Morphix', 'Morphix')
        self._job = None
        self.setWindowTitle(tr('Morphix · Speech → Text'))
        self.setMinimumWidth(540)
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLE)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)

        title = QLabel(tr('Convert speech to text'))
        title.setObjectName('title')
        lay.addWidget(title)
        length = _human_duration(self.paths)
        names = ', '.join(Path(p).name for p in self.paths[:3]) + (' …' if len(self.paths) > 3 else '')
        info = QLabel(tr('{n} file(s)', n=len(self.paths)) + (' · ' + length if length else '') + '\n' + names
                      if self.paths else
                      tr('Download a speech model once. After that, Arabic and English transcription '
                         'works completely offline.'))
        info.setObjectName('hint')
        info.setWordWrap(True)
        lay.addWidget(info)

        card = QFrame()
        card.setObjectName('card')
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(9)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Language')))
        self.language = QComboBox()
        self.language.addItem(tr('Detect automatically (Arabic / English)'), 'auto')
        self.language.addItem(tr('Arabic'), 'ar')
        self.language.addItem(tr('English'), 'en')
        self._select(self.language, self.settings.value('transcribe/language', 'auto'))
        row.addWidget(self.language, 1)
        form.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Accuracy')))
        self.quality = QComboBox()
        for key, (_alias, size, label) in te.MODELS.items():
            mark = '  ✓' if te.model_dir(key) else ''
            self.quality.addItem(f'{tr(label)}  ·  {size}{mark}', key)
        self._select(self.quality, self.settings.value('transcribe/quality', te.DEFAULT_QUALITY))
        self.quality.currentIndexChanged.connect(self._refresh_model)
        row.addWidget(self.quality, 1)
        form.addLayout(row)

        saved = str(self.settings.value('transcribe/formats', 'txt,srt')).split(',')
        self.fmt = {}
        fmts = QHBoxLayout()
        for key, label in (('txt', 'Text (.txt)'), ('txt_ts', 'Text + times'),
                           ('srt', 'Subtitles (.srt)'), ('vtt', 'WebVTT')):
            box = QCheckBox()
            box.setChecked(key in saved)
            self.fmt[key] = box
            fmts.addWidget(option_row(box, tr(label), wrap=False))
        form.addLayout(fmts)
        self.clean = QCheckBox()
        self.clean.setChecked(self.settings.value('transcribe/clean', True, type=bool))
        form.addWidget(option_row(self.clean, tr('Clean up the audio first (evens out quiet voices, removes rumble)')))
        lay.addWidget(card)

        self.model_state = QLabel()
        self.model_state.setWordWrap(True)
        lay.addWidget(self.model_state)
        self.download = QPushButton(tr('Download this model (one time)'))
        self.download.clicked.connect(self._download)
        lay.addWidget(self.download)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.hide()
        lay.addWidget(self.bar)

        note = QLabel(tr('For Arabic choose “Most accurate”, or “Maximum accuracy” for the very best result '
                         '(same 3 GB download, about half the speed). '
                         'Clear recordings work best — strong dialects and heavy background noise lower accuracy.') + '\n' +
                      tr('Runs 100% on this computer. Long recordings (hours) are processed in parts; '
                         'if you cancel or the Mac sleeps, run it again on the same file to continue.'))
        note.setObjectName('hint')
        note.setWordWrap(True)
        lay.addWidget(note)

        buttons = QDialogButtonBox()
        self.start = buttons.addButton(tr('Start'), QDialogButtonBox.AcceptRole)
        self.start.setObjectName('primary')
        buttons.addButton(tr('Cancel'), QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self._refresh_model()

    @staticmethod
    def _select(combo, value):
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _refresh_model(self):
        quality = self.quality.currentData()
        engine_ok = te.engine_available()
        installed = te.model_dir(quality) is not None
        if not engine_ok:
            self.model_state.setObjectName('warn')
            self.model_state.setText(tr('The speech engine is not installed. Run Launch_Morphix_Mac.command '
                                        'once while connected to the internet.'))
        elif installed:
            self.model_state.setObjectName('ok')
            self.model_state.setText('✓ ' + tr('Model installed — works offline.'))
        else:
            self.model_state.setObjectName('warn')
            self.model_state.setText(tr('This model is not downloaded yet ({size}). Internet is needed '
                                        'only for this one-time download.', size=te.MODELS[quality][1]))
        self.model_state.style().unpolish(self.model_state)
        self.model_state.style().polish(self.model_state)
        busy = self._job is not None
        self.download.setVisible(engine_ok and not installed)
        self.download.setEnabled(not busy)
        self.start.setEnabled((engine_ok and installed and not busy) or (not self.paths and not busy))

    def _download(self):
        from conversion_job import ConversionJob
        self.bar.show()
        self.bar.setRange(0, 0)          # indeterminate: HF gives no reliable total
        self._job = ConversionJob('download_speech_model', [], str(te.models_root()),
                                  {'quality': self.quality.currentData()}, parent=self)
        self._job.status.connect(self.model_state.setText)
        self._job.completed.connect(lambda _o: None)
        self._job.failed.connect(lambda e: QMessageBox.warning(self, tr('Download failed'), e[-1500:]))
        self._job.finished.connect(self._download_done)
        self._refresh_model()
        self._job.start()

    def _download_done(self):
        self._job.deleteLater()
        self._job = None
        self.bar.hide()
        self.bar.setRange(0, 100)
        self._refresh_model()

    def _accept(self):
        if not any(b.isChecked() for b in self.fmt.values()):
            self.fmt['txt'].setChecked(True)
        self.settings.setValue('transcribe/language', self.language.currentData())
        self.settings.setValue('transcribe/quality', self.quality.currentData())
        self.settings.setValue('transcribe/formats', ','.join(k for k, b in self.fmt.items() if b.isChecked()))
        self.settings.setValue('transcribe/clean', self.clean.isChecked())
        self.accept()

    def reject(self):
        if self._job is not None:
            self._job.cancel()
        super().reject()

    def options(self):
        return {'language': self.language.currentData(),
                'quality': self.quality.currentData(),
                'formats': [k for k, b in self.fmt.items() if b.isChecked()] or ['txt'],
                'clean_audio': self.clean.isChecked()}


def ask_transcription_options(paths, parent=None):
    dialog = TranscriptionDialog(paths, parent)
    dialog.setWindowFlag(Qt.WindowStaysOnTopHint, parent is None)
    if dialog.exec() != QDialog.Accepted:
        return None
    return dialog.options()
