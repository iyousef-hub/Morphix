"""Video / audio compression window (Morphix 1.11).

Pick Recommended, choose a strength, or give a target size (e.g. 25 MB). While the
slider or size changes, a five-step meter and a plain sentence say what the quality
will be — from “looks the same” down to “heavy blocks” — before anything runs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout, QSlider, QCheckBox, QPushButton,
                               QDoubleSpinBox, QButtonGroup, QWidget, QFrame, QStackedWidget)

import media_compress as mc
from compression_dialog import nice_size
from i18n import tr, option_row, slider_css

LEVEL_COLORS = ('#FF6B6B', '#FFA94D', '#FFD43B', '#69DB7C', '#38D9A9')
LEVEL_NAMES = ('Very poor', 'Low', 'Acceptable', 'Good', 'Excellent')
TARGET_CHIPS = (8, 10, 16, 25, 50, 100)
MODES = (('recommended', 'Recommended'), ('strength', 'Choose the strength'), ('target', 'Target size'))


class MediaCompressDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = [str(p) for p in paths]
        self.infos = {}
        self.settings = QSettings('Morphix', 'Morphix')
        self.setWindowTitle(tr('Morphix · Compress video and audio'))
        self.setMinimumWidth(500)
        self.setModal(True)
        self.setStyleSheet('''
            QDialog { background: #0A1B31; color: #EBF5FF; }
            QLabel { color: #DCEBFA; background: transparent; }
            QLabel#muted { color: #91B3D5; }
            QLabel#big { font-size: 17px; font-weight: 750; color: #ACD9FF; }
            QLabel#verdict { font-size: 14px; font-weight: 650; }
            QPushButton { border: 1px solid #426D9E; border-radius: 9px; padding: 9px 14px;
                          background: #17314E; color: white; }
            QPushButton:checked { background: #2379D9; border-color: #8CC8FF; font-weight: 700; }
            QPushButton#chip { padding: 6px 10px; border-radius: 13px; }
            QPushButton#primary { background: #2379D9; border-color: #66B4FF; font-weight: 700; }
            QPushButton#primary:disabled { background: #22374F; color: #7D93AA; border-color: #33506F; }
            QDoubleSpinBox { border: 1px solid #426D9E; border-radius: 9px; padding: 7px; color: #EAF5FF;
                             background: #193351; font-size: 15px; }
            QFrame#card { background: #10263F; border: 1px solid #284B70; border-radius: 12px; }
            QWidget#optionRow { background: transparent; }
            QLabel#optionLabel { color: #DCEBFA; }
        ''' + slider_css('#294666', '#4EA4FF', '#C0E2FF'))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(11)
        title = QLabel(tr('Compress video and audio'))
        title.setObjectName('big')
        lay.addWidget(title)
        total = sum(Path(p).stat().st_size for p in self.paths if Path(p).exists())
        self.source = QLabel(tr('{n} file(s)', n=len(self.paths)) + ' · ' + tr('Original size:') + ' '
                             + nice_size(total))
        self.source.setObjectName('muted')
        lay.addWidget(self.source)

        # ---- mode buttons
        mode_row = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        for i, (key, label) in enumerate(MODES):
            b = QPushButton(tr(label))
            b.setCheckable(True)
            b.setProperty('mode', key)
            self.mode_group.addButton(b, i)
            mode_row.addWidget(b)
        lay.addLayout(mode_row)

        self.pages = QStackedWidget()
        # recommended
        rec = QLabel(tr('The best balance: clear picture, much smaller file. Large videos are limited to '
                        'Full HD (1080p); sound stays clear.'))
        rec.setWordWrap(True)
        rec.setObjectName('muted')
        self.pages.addWidget(self._wrap(rec))
        # strength
        sw = QWidget()
        sl = QVBoxLayout(sw)
        sl.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr('Compression strength')))
        top.addStretch()
        self.strength_label = QLabel('')
        top.addWidget(self.strength_label)
        sl.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        sl.addWidget(self.slider)
        ends = QHBoxLayout()
        a, b = QLabel(tr('Lighter · best quality')), QLabel(tr('Stronger · smallest file'))
        a.setObjectName('muted'); b.setObjectName('muted')
        ends.addWidget(a); ends.addStretch(); ends.addWidget(b)
        sl.addLayout(ends)
        self.pages.addWidget(sw)
        # target size
        tw = QWidget()
        tl = QVBoxLayout(tw)
        tl.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel(tr('Each file at most')))
        self.target = QDoubleSpinBox()
        self.target.setRange(1, 4000)
        self.target.setDecimals(0)
        self.target.setSuffix(' MB')
        self.target.setMinimumWidth(120)
        r.addWidget(self.target)
        r.addStretch()
        tl.addLayout(r)
        chips = QHBoxLayout()
        for mb in TARGET_CHIPS:
            c = QPushButton(f'{mb} MB')
            c.setObjectName('chip')
            c.clicked.connect(lambda _=False, v=mb: self.target.setValue(v))
            chips.addWidget(c)
        chips.addStretch()
        tl.addLayout(chips)
        hint = QLabel(tr('Handy limits: WhatsApp 16 MB · Email 25 MB · Discord 10 MB. '
                         'Whatever the original size, the result will not be bigger than this.'))
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        tl.addWidget(hint)
        self.pages.addWidget(tw)
        lay.addWidget(self.pages)

        self.keep_res = QCheckBox()
        self.keep_row = option_row(self.keep_res, tr('Keep the original resolution (do not make the picture smaller)'))
        lay.addWidget(self.keep_row)

        # ---- live quality card
        card = QFrame()
        card.setObjectName('card')
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(7)
        meter_row = QHBoxLayout()
        meter_row.setSpacing(4)
        self.segments = []
        for _ in range(5):
            seg = QFrame()
            seg.setFixedHeight(8)
            self.segments.append(seg)
            meter_row.addWidget(seg)
        cl.addLayout(meter_row)
        self.verdict = QLabel(tr('Reading the files…'))
        self.verdict.setObjectName('verdict')
        self.verdict.setWordWrap(True)
        cl.addWidget(self.verdict)
        self.estimate = QLabel('')
        self.estimate.setObjectName('muted')
        self.estimate.setWordWrap(True)
        cl.addWidget(self.estimate)
        self.details = QLabel('')
        self.details.setObjectName('muted')
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.PlainText)
        cl.addWidget(self.details)
        lay.addWidget(card)

        note = QLabel(tr('Saved as new files next to the originals — your originals are never changed.'))
        note.setObjectName('muted')
        note.setWordWrap(True)
        lay.addWidget(note)
        buttons = QHBoxLayout()
        cancel = QPushButton(tr('Cancel'))
        self.confirm = QPushButton(tr('Compress'))
        self.confirm.setObjectName('primary')
        self.confirm.setEnabled(False)
        buttons.addWidget(cancel)
        buttons.addWidget(self.confirm)
        lay.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        self.confirm.clicked.connect(self._accept)

        # ---- restore last choices
        s = self.settings
        mode = s.value('media_compress/mode', 'recommended')
        idx = next((i for i, (k, _) in enumerate(MODES) if k == mode), 0)
        self.mode_group.button(idx).setChecked(True)
        self.pages.setCurrentIndex(idx)
        self.slider.setValue(self._int(s.value('media_compress/strength', 50), 50))
        self.target.setValue(self._int(s.value('media_compress/target_mb', 25), 25))
        self.keep_res.setChecked(s.value('media_compress/keep_res', False, type=bool))
        self.mode_group.idClicked.connect(self._mode_changed)
        self.slider.valueChanged.connect(self._schedule)
        self.target.valueChanged.connect(self._schedule)
        self.keep_res.toggled.connect(self._schedule)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._update)
        self._paint_meter(-1)

        # Probe in the background (ffmpeg reads each header; fast, but many files add up).
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.futures = {p: self.pool.submit(mc.probe, p) for p in self.paths}
        self.poll = QTimer(self)
        self.poll.setInterval(80)
        self.poll.timeout.connect(self._collect)
        self.poll.start()
        self._mode_changed(idx, schedule=False)

    @staticmethod
    def _int(v, default):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _wrap(widget):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(widget)
        return w

    # ------------------------------------------------------------ state
    def mode(self):
        return MODES[max(0, self.mode_group.checkedId())][0]

    def _mode_changed(self, idx, schedule=True):
        self.pages.setCurrentIndex(idx)
        has_video = any(i.get('video') for i in self.infos.values()) or not self.infos
        self.keep_row.setVisible(has_video and self.mode() != 'recommended')
        if schedule:
            self._schedule()

    def _schedule(self, *_):
        self.strength_label.setText(f'{self.slider.value()}%')
        self.timer.start()

    def _collect(self):
        for p, f in list(self.futures.items()):
            if f.done():
                del self.futures[p]
                try:
                    self.infos[p] = f.result()
                except Exception as exc:  # unreadable file
                    self.infos[p] = {'name': Path(p).name, 'size': 0, 'duration': 0, 'video': False,
                                     'audio': False, 'error': str(exc)}
        if not self.futures:
            self.poll.stop()
            self.pool.shutdown(wait=False)
            self._mode_changed(self.mode_group.checkedId(), schedule=False)
            self._update()

    def plans(self):
        out = []
        for p in self.paths:
            info = self.infos.get(p)
            if info is None:
                continue
            if info.get('error'):
                out.append({'name': info['name'], 'ok': False, 'level': 0, 'size': 0, 'est': 0,
                            'message': 'This file could not be read.'})
                continue
            out.append(mc.plan(info, self.mode(), self.slider.value(), self.target.value(),
                               self.keep_res.isChecked()))
        return out

    def _paint_meter(self, level):
        color = LEVEL_COLORS[level] if level >= 0 else '#2A4462'
        for i, seg in enumerate(self.segments):
            on = level >= 0 and i <= level
            seg.setStyleSheet(f'background:{color if on else "#22384F"}; border-radius:4px;')
        if level >= 0:
            self.verdict.setStyleSheet(f'color:{color};')

    def _update(self):
        self.strength_label.setText(f'{self.slider.value()}%')
        if self.futures:
            return
        plans = self.plans()
        ok = [p for p in plans if p.get('ok')]
        level, message = mc.summary(plans)
        self._paint_meter(level if ok else 0)
        self.verdict.setText(tr(message))
        self.confirm.setEnabled(bool(ok))
        before = sum(p['size'] for p in ok)
        after = sum(p['est'] for p in ok)
        lines = []
        if ok:
            pct = max(0, round((1 - after / max(before, 1)) * 100))
            self.estimate.setText(tr('Estimated result: {before} → about {after} (≈{pct}% smaller)',
                                     before=nice_size(before), after=nice_size(after), pct=pct))
        else:
            self.estimate.setText('')
        notes = set()
        for p in plans:
            if len(plans) > 1 or not p.get('ok'):
                if p.get('ok'):
                    lines.append(f"• {p['name']}: {nice_size(p['size'])} → ~{nice_size(p['est'])} · "
                                 + tr(LEVEL_NAMES[p['level']]))
                else:
                    lines.append(f"• {p['name']}: " + tr(p['message']))
            notes.add(p.get('note') or '')
            if p.get('resized') and len(plans) == 1:
                lines.append(tr('Picture size: {size}', size=p['resized']))
        if 'already_small' in notes:
            lines.append(tr('Files already under this size are kept exactly as they are.'))
        if 'little_gain' in notes:
            lines.append(tr('Some files are already well compressed — the saving will be small.'))
        if len(lines) > 9:
            lines = lines[:8] + [tr('…and {n} more', n=len(lines) - 8)]
        self.details.setText('\n'.join(lines))
        self.details.setVisible(bool(lines))
        # Plain multi-line text: reserve its height so the card never clips the last lines.
        self.details.setMinimumHeight(self.details.fontMetrics().lineSpacing() * len(lines) + 10 if lines else 0)
        if self.isVisible():
            self.adjustSize()

    def _accept(self):
        s = self.settings
        s.setValue('media_compress/mode', self.mode())
        s.setValue('media_compress/strength', self.slider.value())
        s.setValue('media_compress/target_mb', int(self.target.value()))
        s.setValue('media_compress/keep_res', self.keep_res.isChecked())
        self.accept()

    def options(self):
        return {'mc_mode': self.mode(), 'mc_strength': self.slider.value(),
                'mc_target_mb': float(self.target.value()), 'mc_keep_res': self.keep_res.isChecked()}

    def done(self, r):
        try:
            self.poll.stop()
            self.pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        super().done(r)
