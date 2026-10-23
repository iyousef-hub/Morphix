"""Morphix bilingual interface (English / العربية).

Usage:  tr('English text')  → the Arabic text when Arabic is selected.
Strings are keyed by their English wording; anything missing falls back to
English, so the app never shows an empty label. The Arabic is written to be
natural and clear, not a word-for-word translation.

This module imports Qt lazily so the conversion worker can use trl() too.
"""
from __future__ import annotations

import os
import sys

LANGS = ('en', 'ar')
_lang = None


def _settings():
    from PySide6.QtCore import QSettings
    return QSettings('Morphix', 'Morphix')


def chosen():
    """The saved language, or None when the user has not chosen yet."""
    try:
        value = str(_settings().value('language', '') or '')
    except Exception:
        return None
    return value if value in LANGS else None


def current():
    global _lang
    if _lang is None:
        _lang = os.environ.get('MORPHIX_LANG') or chosen() or 'en'
        if _lang not in LANGS:
            _lang = 'en'
    return _lang


def set_language(code, save=True):
    global _lang
    if code not in LANGS:
        raise ValueError(code)
    _lang = code
    if save:
        s = _settings()
        s.setValue('language', code)
        s.sync()


def is_rtl():
    return current() == 'ar'


# On Windows the Mac words in the interface are swapped for their Windows
# equivalents, so one set of strings (and translations) serves both systems.
WINDOWS_WORDS = {
    'en': (('Launch_Morphix_Mac.command', 'Morphix setup'), ('Show in Finder', 'Show in folder'), ('a Finder window', 'a File Explorer window'),
           ('Finder', 'File Explorer'), ('the menu bar', 'the taskbar tray (near the clock)'),
           ('menu bar', 'taskbar tray'), ('⌘ Command', 'Win'), ('⌘', 'Win'), ('Option + ', 'Alt + '),
           ('macOS', 'Windows'), ('This Mac', 'This computer'), ('this Mac', 'this computer'),
           ('the Mac', 'the computer'), ('a Mac', 'a computer')),
    'ar': (('Launch_Morphix_Mac.command', 'برنامج تثبيت Morphix'), ('Finder', 'مستكشف الملفات'), ('شريط القوائم', 'منطقة الأيقونات بجانب الساعة'),
           ('⌘ Command', 'Win'), ('⌘', 'Win'), ('Option + ', 'Alt + '), ('macOS', 'Windows'),
           ('جهاز Mac', 'جهاز')),
}


def for_windows(text, lang='en'):
    for mac, win in WINDOWS_WORDS.get(lang, ()):
        text = text.replace(mac, win)
    return text


def trl(lang, text, **fmt):
    out = AR.get(text, text) if lang == 'ar' else text
    if fmt:
        try:
            out = out.format(**fmt)
        except (KeyError, IndexError, ValueError):
            out = text.format(**fmt)
    if sys.platform == 'win32':
        out = for_windows(out, lang)
    return out


def tr(text, **fmt):
    return trl(current(), text, **fmt)


def amp(text):
    """Qt treats '&' in buttons/menus as a shortcut marker; show it literally."""
    return text.replace('&', '&&')


def start_side():
    """'left' in English, 'right' in Arabic — for stylesheet text alignment."""
    return 'right' if is_rtl() else 'left'


def apply(app):
    """Layout direction + a font that renders Arabic beautifully."""
    from PySide6.QtCore import Qt
    app.setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)
    # Bundled IBM Plex Sans Arabic (Arabic + Latin) and the dark palette.
    import theme
    theme.apply(app)


def ensure_language(app):
    """First launch: ask once, in both languages."""
    if chosen():
        apply(app)
        return current()
    import theme
    theme.apply(app)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    from PySide6.QtGui import QPixmap
    from app_assets import logo_png
    dlg = QDialog()
    dlg.setWindowTitle('Morphix')
    dlg.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    dlg.setFixedWidth(460)
    dlg.setStyleSheet('''
        QDialog { background:#081629; }
        QLabel { color:#E7F2FF; background:transparent; }
        QLabel#t { font-size:22px; font-weight:800; }
        QLabel#s { color:#93B3D6; font-size:13px; }
        QPushButton { color:white; background:#173458; border:1px solid #3A6DA3; border-radius:14px;
                      padding:18px; font-size:19px; font-weight:700; }
        QPushButton:hover { background:#2477D8; border-color:#7BB8FF; }
    ''')
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(30, 26, 30, 28)
    lay.setSpacing(12)
    logo = QLabel()
    logo.setAlignment(Qt.AlignCenter)
    logo.setPixmap(QPixmap(logo_png()).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    lay.addWidget(logo)
    t = QLabel('اختر لغة البرنامج  ·  Choose your language')
    t.setObjectName('t'); t.setAlignment(Qt.AlignCenter)
    lay.addWidget(t)
    s = QLabel('يمكنك تغييرها لاحقًا من الإعدادات  ·  You can change it later in Settings')
    s.setObjectName('s'); s.setAlignment(Qt.AlignCenter); s.setWordWrap(True)
    lay.addWidget(s)
    lay.addSpacing(8)
    row = QHBoxLayout()
    row.setSpacing(14)
    picked = {'v': 'en'}
    for label, code in (('العربية', 'ar'), ('English', 'en')):
        b = QPushButton(label)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, c=code: (picked.update(v=c), dlg.accept()))
        row.addWidget(b)
    lay.addLayout(row)
    dlg.exec()
    set_language(picked['v'])
    apply(app)
    return current()


def relaunch_args(extra=('--studio',)):
    """Command that starts Morphix again (source or packaged build)."""
    from pathlib import Path
    if getattr(sys, 'frozen', False):
        return [sys.executable, *extra]
    return [sys.executable, str(Path(__file__).resolve().with_name('main.py')), *extra]


def spawn_relaunch(delay=1.3, extra=('--studio',)):
    """Start a fresh Morphix after `delay` seconds (this process should then quit)."""
    import subprocess
    args = relaunch_args((*extra, '--delay-start', str(delay)))
    env = dict(os.environ)
    if not getattr(sys, 'frozen', False):
        try:
            from qt_macos_runtime import clean_qt_environment
            env = clean_qt_environment()
        except Exception:
            pass
    env.pop('MORPHIX_LANG', None)
    kwargs = {'stdin': subprocess.DEVNULL}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x00000008 | 0x00000200   # DETACHED | NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True
    subprocess.Popen(args, env=env, **kwargs)


from i18n_ar import AR  # noqa: E402  (large dictionary kept in its own file)


def slider_css(groove='#29425F', fill='#378DF1', handle='#AFD7FF'):
    """Slider colours that fill from the correct side (Qt style sheets draw the
    'sub-page' on the left even in right-to-left layouts, so swap them)."""
    filled, empty = ('add-page', 'sub-page') if is_rtl() else ('sub-page', 'add-page')
    return (f'QSlider::groove:horizontal {{ height:5px; border-radius:3px; background:{groove}; }}'
            f'QSlider::{filled}:horizontal {{ background:{fill}; border-radius:3px; }}'
            f'QSlider::{empty}:horizontal {{ background:{groove}; border-radius:3px; }}'
            f'QSlider::handle:horizontal {{ background:{handle}; width:16px; margin:-6px 0; border-radius:8px; }}')


def option_row(button, text, wrap=True):
    """A check box / radio button whose indicator sits at the start of the
    line — on the right in Arabic — right next to its (wrapping) label."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
    row = QWidget()
    row.setObjectName('optionRow')
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(8)
    button.setText('')
    button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    label = QLabel(text)
    label.setWordWrap(wrap)
    label.setCursor(Qt.PointingHandCursor)
    label.setObjectName('optionLabel')
    label.mousePressEvent = lambda _e: button.click()
    label.setEnabled(button.isEnabled())
    lay.addWidget(button, 0, Qt.AlignTop)
    lay.addWidget(label, 1)
    row.button, row.label = button, label
    return row
