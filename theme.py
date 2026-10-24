"""App-wide look: bundled IBM Plex Sans Arabic font + a dark palette.

Many small windows (page ranges, message boxes, tooltips, menus, scroll areas)
only style part of their widgets. On Windows the native style then fills the
rest with its light system colours, giving white strips inside dark dialogs.
A dark palette (and the Fusion style on Windows, which honours it fully)
makes every unstyled surface match the Morphix colours.
"""
from __future__ import annotations

import sys

from app_assets import ASSETS

FONT_FAMILY = 'IBM Plex Sans Arabic'
_FONT_FILES = ('IBMPlexSansArabic-Regular.ttf', 'IBMPlexSansArabic-Medium.ttf',
               'IBMPlexSansArabic-SemiBold.ttf', 'IBMPlexSansArabic-Bold.ttf')
_loaded = None

BG = '#0B182C'          # window background
BASE = '#122943'        # inputs, lists
ALT = '#16304F'
TEXT = '#E9F4FF'
MUTED = '#8EA6C4'
BUTTON = '#163657'
ACCENT = '#287BE2'

GLOBAL_CSS = f'''
QToolTip {{ background:#14294A; color:{TEXT}; border:1px solid #3A6497; border-radius:6px; padding:5px 8px; }}
QMenu {{ background:#0F2038; color:{TEXT}; border:1px solid #2C4C74; border-radius:8px; padding:5px; }}
QMenu::item {{ padding:7px 22px; border-radius:6px; }}
QMenu::item:selected {{ background:#2367BC; color:#FFFFFF; }}
QMenu::item:disabled {{ color:#6F89AA; }}
QMenu::separator {{ height:1px; background:#24426A; margin:5px 8px; }}
QMessageBox, QInputDialog {{ background:{BG}; }}
QMessageBox QLabel {{ color:{TEXT}; }}
'''


def load_fonts():
    """Register the bundled fonts once; returns True when the family is usable."""
    global _loaded
    if _loaded is not None:
        return _loaded
    from PySide6.QtGui import QFontDatabase
    ok = False
    for name in _FONT_FILES:
        path = ASSETS / 'fonts' / name
        if path.is_file() and QFontDatabase.addApplicationFont(str(path)) != -1:
            ok = True
    _loaded = ok
    if not ok:
        print('[Morphix] Bundled font not found; using the system font.', flush=True)
    return ok


def apply_font(app):
    from PySide6.QtGui import QFont
    font = QFont(app.font())
    families = []
    if load_fonts():
        families.append(FONT_FAMILY)
    if sys.platform == 'darwin':
        families += ['SF Arabic', '.AppleSystemUIFont', 'Geeza Pro']
    else:
        families += ['Segoe UI', 'Tahoma']
    font.setFamilies(families)
    if font.pointSizeF() < 9.5:
        font.setPointSizeF(9.5)
    app.setFont(font)


def apply_palette(app):
    from PySide6.QtGui import QPalette, QColor
    if sys.platform == 'win32':
        # The Windows 11 native style ignores parts of the palette; Fusion
        # follows it everywhere, and the stylesheets give it the Morphix look.
        app.setStyle('Fusion')
    pal = QPalette()
    colors = {
        QPalette.Window: BG, QPalette.WindowText: TEXT, QPalette.Base: BASE,
        QPalette.AlternateBase: ALT, QPalette.ToolTipBase: '#14294A', QPalette.ToolTipText: TEXT,
        QPalette.Text: TEXT, QPalette.Button: BUTTON, QPalette.ButtonText: TEXT,
        QPalette.BrightText: '#FFFFFF', QPalette.Highlight: ACCENT, QPalette.HighlightedText: '#FFFFFF',
        QPalette.Link: '#7DB9FF', QPalette.PlaceholderText: MUTED, QPalette.Light: '#2C4C74',
        QPalette.Midlight: '#21406A', QPalette.Mid: '#1A3355', QPalette.Dark: '#081221',
        QPalette.Shadow: '#000000',
    }
    for role, value in colors.items():
        pal.setColor(role, QColor(value))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor('#5F7898'))
    app.setPalette(pal)
    app.setStyleSheet(GLOBAL_CSS)


class _DialogFitter:
    """Grow every dialog to the height its content really needs when it opens.

    Qt sizes a new window from its layout's plain size hint, which ignores how
    much taller word-wrapped text becomes at the window's actual width. With a
    tall font (IBM Plex Sans Arabic) this squeezed drop-downs and cut off the
    last lines of wrapped labels. Only ever grows, and never past the screen.
    """

    def __init__(self, app):
        from PySide6.QtCore import QObject, QEvent

        class Filter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Show:
                    from PySide6.QtWidgets import QDialog
                    if isinstance(obj, QDialog):
                        fit_height(obj)
                return False
        self.filter = Filter(app)
        app.installEventFilter(self.filter)


def fit_height(window):
    layout = window.layout()
    if layout is None:
        return
    layout.activate()
    width = window.width()
    if layout.hasHeightForWidth():
        need = layout.totalHeightForWidth(width)
    else:
        need = layout.totalSizeHint().height()
    need = max(need, layout.totalMinimumSize().height())
    screen = window.screen()
    if screen is not None:
        need = min(need, screen.availableGeometry().height() - 40)
    if need > window.height():
        window.resize(width, need)


_fitter = None


def apply(app):
    global _fitter
    apply_font(app)
    apply_palette(app)
    if _fitter is None:
        _fitter = _DialogFitter(app)
