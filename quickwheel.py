"""Morphix Action Hub (formerly Quick Wheel): Finder selection + global shortcut + overlay.

macOS selection comes from Finder via AppleScript; global shortcuts use an AppKit
main-thread monitor on macOS (fixes the v0.6 crash). Windows uses pynput.
Explorer selection uses pywin32 on Windows.
Installers must be built on each target operating system; unsigned builds need manual testing.
"""
from __future__ import annotations

import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from app_assets import logo_png
from i18n import tr

from PySide6.QtCore import Qt, QObject, Signal, QPointF, QRectF, QSize, QSettings, QTimer, QEasingCurve, QPropertyAnimation, QProcess, QUrl
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QBrush, QPixmap, QCursor, QGuiApplication, QDesktopServices
from PySide6.QtWidgets import (QWidget, QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QComboBox, QLineEdit, QListWidget, QListWidgetItem, QFileDialog,
    QSystemTrayIcon, QMenu, QMessageBox, QCheckBox, QFrame, QSpinBox, QSlider)

PROFILES = {
    'pdf_single': ('One PDF', ['ocr_searchable_pdf','organize_pdf','sign_pdf','optimize_pdf','pdf_word','extract_pdf_text','pdf_png_zip','split_pdf','visual_pdf']),
    'pdf_image_mix': ('PDF + Images', ['merge_pdf','merge_optimize','zip_files','tar_gz_files','rar_files']),
    'pdf_multi': ('Multiple PDFs', ['merge_pdf','merge_optimize','sign_pdf','ocr_searchable_pdf','optimize_pdf','extract_pdf_text','pdf_png_zip','zip_files']),
    'image_single': ('One image', ['heic_jpg','remove_bg','images_pdf','ocr_image_text','sign_images','visual_image','image_compress','image_jpg','more_actions']),
    'image_multi': ('Multiple images', ['heic_jpg','images_pdf','remove_bg','sign_images','ocr_image_text','image_jpg','image_compress','zip_files']),
    'video_single': ('One video', ['ppt_media','trim_media','transcribe_media','video_mp3','video_mp4','zip_files']),
    'video_multi': ('Multiple videos', ['ppt_media','transcribe_media','join_video','video_mp3','video_mp4','zip_files']),
    'audio_single': ('One audio', ['ppt_media','trim_media','transcribe_media','audio_mp3','zip_files']),
    'audio_multi': ('Multiple audio', ['ppt_media','transcribe_media','join_audio','audio_mp3','zip_files']),
    'office': ('Word / PowerPoint files', ['office_pdf','docs_merge_pdf','zip_files','tar_gz_files']),
    'excel_single': ('One Excel file', ['office_pdf','xlsx_pdf_fit','xlsx_csv','xlsx_split','csv_xlsx','zip_files']),
    'excel_multi': ('Multiple Excel files', ['xlsx_merge','docs_merge_pdf','office_pdf','xlsx_csv','csv_xlsx','zip_files']),
    'docs_mix': ('Mixed documents', ['docs_merge_pdf','docs_pdf_each','zip_files','tar_gz_files']),
    'mixed': ('Mixed files', ['zip_files','tar_gz_files','rar_files']),
}

WHEEL_LABELS = {
    'pdf_png_zip': ('To PNG','image'), 'pdf_jpg_zip': ('To JPG','image'),
    'optimize_pdf': ('Compress','compress'), 'split_pdf': ('Extract range','split'),
    'separate_pdf': ('Separate PDF','split'), 'ocr_image_text': ('Extract text','text'),
    'merge_pdf': ('Merge to PDF','merge'), 'merge_optimize': ('Merge + Compress','merge'),
    'visual_pdf': ('Edit PDF','edit'), 'visual_image': ('Crop & rotate','edit'),
    'images_pdf': ('Make PDF','pdf'), 'image_jpg': ('To JPG','image'),
    'image_png': ('To PNG','image'), 'image_webp': ('To WebP','image'),
    'image_compress': ('Compress','compress'), 'image_resize': ('Resize','resize'),
    'video_mp3': ('Extract audio','audio'), 'video_mp4': ('To MP4','video'),
    'join_video': ('Merge videos','merge'), 'audio_mp3': ('To MP3','audio'),
    'join_audio': ('Merge audio','merge'), 'office_pdf': ('To PDF','pdf'),
    'zip_files': ('ZIP files','zip'), 'tar_gz_files': ('TAR.GZ','zip'), 'rar_files': ('RAR (licensed)','zip'),
    'extract_pdf_text': ('Extract text','text'), 'ocr_pdf_text': ('OCR → Text file','text'),
    'ocr_searchable_pdf': ('OCR','ocr'),
    'transcribe_media': ('Speech → Text','speech'),
    'remove_bg': ('Remove background','cutout'),
    'docs_merge_pdf': ('Merge into one PDF','merge'), 'docs_pdf_each': ('Each to PDF','pdf'),
    'xlsx_pdf_fit': ('PDF · fit sheets','pdf'), 'xlsx_csv': ('To CSV','table'),
    'xlsx_split': ('Split sheets','split'), 'xlsx_merge': ('Merge workbooks','merge'),
    'csv_xlsx': ('To Excel','table'),
    'ppt_media': ('PowerPoint-ready','slides'), 'trim_media': ('Trim','trim'),
    'heic_jpg': ('HEIC → JPG','image'), 'pdf_word': ('To Word','word'),
    'organize_pdf': ('Organize pages','pages'), 'sign_pdf': ('Sign','sign'), 'sign_images': ('Signature','sign'),
    'more_actions': ('More tools','more'), 'studio': ('Open Studio','more'),
}

DEFAULT_SHORTCUT = '<cmd>+<shift>+m' if platform.system() == 'Darwin' else '<ctrl>+<shift>+m'


def selection_profile(paths):
    from file_intelligence import selection_profile as profile
    return profile(paths)


def finder_selected_files():
    """Read files currently highlighted in macOS Finder; Finder may ask Automation approval."""
    script = '''tell application "Finder"
    set selectedItems to selection
    set answerText to ""
    repeat with oneItem in selectedItems
        try
            set answerText to answerText & POSIX path of (oneItem as alias) & (ASCII character 10)
        end try
    end repeat
    return answerText
end tell'''
    proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True,
                          timeout=10, errors='replace')
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or 'Finder selection unavailable')
    return [str(p) for item in proc.stdout.splitlines() if (p := Path(item)).is_file()]


def _explorer_active_tab(hwnd):
    """Windows 11 File Explorer has tabs: every tab is a separate shell window
    with the SAME top-level HWND. The visible tab is the first
    ShellTabWindowClass child of the window."""
    try:
        import win32gui
        return win32gui.FindWindowEx(hwnd, 0, 'ShellTabWindowClass', None) or None
    except Exception:
        return None


def _shell_tab_hwnd(window):
    """The ShellTabWindowClass handle that belongs to one shell window (tab)."""
    try:
        import pythoncom
        from win32com.shell import shell as winshell
        SID_STopLevelBrowser = pythoncom.MakeIID('{4C96BE40-915C-11CF-99D3-00AA004AE837}')
        provider = window._oleobj_.QueryInterface(pythoncom.IID_IServiceProvider)
        browser = provider.QueryService(SID_STopLevelBrowser, winshell.IID_IShellBrowser)
        return browser.GetWindow()
    except Exception:
        return None


def _desktop_selected_files():
    """Files selected on the Windows desktop (not part of Shell.Windows())."""
    import win32com.client
    shell = win32com.client.Dispatch('Shell.Application')
    SWC_DESKTOP, SWFO_NEEDDISPATCH = 8, 1
    import pythoncom
    desktop = shell.Windows().FindWindowSW(pythoncom.Empty, pythoncom.Empty, SWC_DESKTOP, 0, SWFO_NEEDDISPATCH)
    desktop = win32com.client.Dispatch(desktop)
    return [item.Path for item in desktop.Document.SelectedItems()]


_last_source_hwnd = 0


def _selection_source_window(user32, ctypes):
    """The window whose selection the Action Hub shows.

    Once the hub (or any Morphix window) is in front, the foreground window is
    Morphix itself; keep reading the File Explorer window / desktop the user
    was in, instead of concluding that nothing is selected and closing the hub.
    """
    global _last_source_hwnd
    import os
    hwnd = int(user32.GetForegroundWindow() or 0)
    pid = ctypes.c_ulong(0)
    if hwnd:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if hwnd and pid.value != os.getpid():
        _last_source_hwnd = hwnd
        return hwnd
    if _last_source_hwnd and user32.IsWindow(_last_source_hwnd):
        return _last_source_hwnd
    return 0


def explorer_selected_files():
    """Read the selection of the foreground File Explorer window (the visible
    tab on Windows 11) or of the desktop. Requires pywin32."""
    try:
        import ctypes
        import win32com.client
    except ImportError as exc:
        raise RuntimeError('Install pywin32 in the development environment to read Windows Explorer selections.') from exc
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    user32 = ctypes.windll.user32
    active_hwnd = _selection_source_window(user32, ctypes)
    if not active_hwnd:
        return []
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(active_hwnd, buf, 256)
    if buf.value in ('Progman', 'WorkerW'):
        try:
            return [p for p in _desktop_selected_files() if Path(p).is_file()]
        except Exception as exc:
            print(f'[Morphix] Desktop selection: {exc}', flush=True)
            return []
    shell = win32com.client.Dispatch('Shell.Application')
    tabs = []
    for window in shell.Windows():
        try:
            if int(window.HWND) == active_hwnd:
                tabs.append(window)
        except (AttributeError, OSError, TypeError, Exception):
            continue
    if not tabs:
        return []
    if len(tabs) > 1:
        visible = _explorer_active_tab(active_hwnd)
        if visible:
            matching = [w for w in tabs if _shell_tab_hwnd(w) == visible]
            if matching:
                tabs = matching
    for window in tabs:
        try:
            paths = [item.Path for item in window.Document.SelectedItems()]
        except Exception:
            continue
        files = [p for p in paths if Path(p).is_file()]
        if files:
            return files
    return []


def get_explorer_selection():
    if platform.system() == 'Darwin':
        return finder_selected_files()
    if platform.system() == 'Windows':
        return explorer_selected_files()
    if platform.system() == 'Linux':
        # File managers on Linux have no common "current selection" API; use
        # the files copied with Ctrl+C (and the right-click Morphix action).
        from linux_integration import clipboard_files
        return clipboard_files()
    return []


def _speech_status():
    try:
        import transcription_engine as te
        if not te.engine_available():
            return tr('Engine not installed (run Launch_Morphix_Mac.command)')
        ready = [tr(te.MODELS[q][2]) for q in te.MODELS if te.model_dir(q)]
        return (tr('Ready') + ' · ' + '، '.join(ready)) if ready else tr('No model downloaded yet (Studio → Speech models)')
    except Exception as exc:
        return f'{tr("Unavailable")} ({exc})'


def validate_shortcut(combo):
    """Validate backward-compatible shortcut notation, including Del/F-keys."""
    from shortcut_logic import is_valid_shortcut
    return is_valid_shortcut(combo)


# Curated accents stay legible on both light and dark desktop wallpapers.
ACCENT_COLORS = {
    'Blue': '#3896FF',
    'Ice': '#67C9F9',
    'Royal': '#697CFD',
    'Violet': '#A580FF',
    'Teal': '#3FD0C7',
}


def _draw_action_icon(p, x, y, kind, color):
    """Native vector pictograms; avoid unavailable Unicode fonts showing squares."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(x, y)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if kind in ('image', 'video'):
        p.drawRoundedRect(QRectF(-13, -10, 26, 20), 3, 3)
        if kind == 'image':
            p.drawEllipse(QPointF(5, -4), 2.5, 2.5)
            path = QPainterPath(QPointF(-10, 7));path.lineTo(-2, -2);path.lineTo(3, 3);path.lineTo(7, 0);path.lineTo(11, 7)
            p.drawPath(path)
        else:
            poly = QPainterPath(QPointF(-3, -6));poly.lineTo(7, 0);poly.lineTo(-3, 6);poly.closeSubpath();p.drawPath(poly)
    elif kind in ('pdf', 'text', 'zip'):
        p.drawRoundedRect(QRectF(-10, -12, 20, 24), 2, 2)
        f=QFont('Arial', 8, QFont.Bold);p.setFont(f)
        p.drawText(QRectF(-11,-6,22,17), Qt.AlignCenter, {'pdf':'PDF','text':'TXT','zip':'ZIP'}[kind])
    elif kind == 'merge':
        p.drawRoundedRect(QRectF(-11,-9,15,19), 2,2)
        p.drawRoundedRect(QRectF(-3,-12,15,19), 2,2)
    elif kind == 'compress':
        p.drawLine(-12,-8,-3,1);p.drawLine(-12,1,-3,1);p.drawLine(-3,-8,-3,1)
        p.drawLine(12,8,3,-1);p.drawLine(12,-1,3,-1);p.drawLine(3,8,3,-1)
    elif kind == 'split':
        p.drawRoundedRect(QRectF(-12,-11,10,22),1,1);p.drawRoundedRect(QRectF(2,-11,10,22),1,1)
    elif kind == 'resize':
        p.drawRect(QRectF(-9,-9,18,18));p.drawLine(2,-9,13,-9);p.drawLine(13,-9,13,2)
    elif kind == 'edit':
        p.drawLine(-10,9,9,-10);p.drawLine(-11,12,-7,3);p.drawLine(6,-12,12,-6)
    elif kind == 'ocr':
        p.drawRoundedRect(QRectF(-12, -12, 17, 22), 2, 2)
        p.drawLine(-8, -6, 1, -6); p.drawLine(-8, -1, -1, -1)
        p.drawEllipse(QPointF(5, 4), 5.5, 5.5)
        p.drawLine(9, 8, 13, 12)
    elif kind == 'speech':
        p.drawRoundedRect(QRectF(-4, -13, 8, 15), 4, 4)
        path = QPainterPath(QPointF(-9, -3)); path.cubicTo(-9, 9, 9, 9, 9, -3); p.drawPath(path)
        p.drawLine(0, 6, 0, 12); p.drawLine(-5, 12, 5, 12)
    elif kind == 'cutout':
        p.drawEllipse(QPointF(0, -6), 5, 5)
        path = QPainterPath(QPointF(-10, 12)); path.cubicTo(-10, 0, 10, 0, 10, 12); p.drawPath(path)
        dash = QPen(color, 1.6, Qt.DashLine); p.setPen(dash)
        p.drawRoundedRect(QRectF(-13, -13, 26, 26), 4, 4)
    elif kind == 'table':
        p.drawRoundedRect(QRectF(-12, -10, 24, 20), 2, 2)
        p.drawLine(-12, -3, 12, -3); p.drawLine(-12, 4, 12, 4); p.drawLine(-4, -10, -4, 10); p.drawLine(4, -10, 4, 10)
    elif kind == 'slides':
        p.drawRoundedRect(QRectF(-13, -10, 26, 18), 2, 2)
        p.drawLine(0, 8, 0, 13); p.drawLine(-5, 13, 5, 13)
        tri = QPainterPath(QPointF(-3, -5)); tri.lineTo(5, -1); tri.lineTo(-3, 3); tri.closeSubpath(); p.drawPath(tri)
    elif kind == 'trim':
        p.drawEllipse(QPointF(-7, 7), 4, 4); p.drawEllipse(QPointF(7, 7), 4, 4)
        p.drawLine(-4, 4, 9, -12); p.drawLine(4, 4, -9, -12)
    elif kind == 'word':
        p.drawRoundedRect(QRectF(-10, -12, 20, 24), 2, 2)
        f = QFont('Arial', 8, QFont.Bold); p.setFont(f)
        p.drawText(QRectF(-11, -6, 22, 17), Qt.AlignCenter, 'DOC')
    elif kind == 'pages':
        for gx, gy in ((-11, -11), (1, -11), (-11, 1), (1, 1)):
            p.drawRoundedRect(QRectF(gx, gy, 10, 10), 1.5, 1.5)
    elif kind == 'sign':
        path = QPainterPath(QPointF(-12, 4)); path.cubicTo(-8, -10, -4, 10, 0, -2); path.cubicTo(3, -9, 6, 8, 12, -1)
        p.drawPath(path); p.drawLine(-12, 11, 12, 11)
    elif kind == 'audio':
        p.drawLine(2,-11,2,7);p.drawLine(2,-11,10,-13)
        p.drawEllipse(QRectF(-6,4,9,7));p.drawEllipse(QRectF(4,2,9,7))
    else:
        for px in (-8,0,8):p.drawEllipse(QPointF(px,0),1.5,1.5)
    p.restore()


def _render_wheel(p: QPainter, width: int, actions, paths, opacity: int,
                  accent_hex: str, glow: int = 58, hover: int = -1, draw_controls: bool = True):
    """Single painter shared by the real desktop overlay and the live preview."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(width / 360.0, width / 360.0)
    origin = QPointF(180, 180)
    accent = QColor(accent_hex)
    strength = max(0, min(100, int(glow))) / 100.0
    alpha = max(25, min(95, int(opacity))) * 255 // 100
    p.setPen(Qt.NoPen)
    # Subtle luminous halo -- translucent, without a large opaque rectangle.
    for radius, base_opacity in [(174, 16), (169, 22), (164, 19)]:
        halo = QColor(accent)
        halo.setAlpha(int(base_opacity * strength))
        p.setBrush(halo)
        p.drawEllipse(origin, radius, radius)
    count = len(actions)
    if not count:
        p.restore()
        return
    span = 360.0 / count
    outer = QRectF(22, 22, 316, 316)
    inner = QRectF(123, 123, 114, 114)
    for i, key in enumerate(actions):
        angle = 90.0 - (i - 0.5) * span - 1.5
        sweep = -(span - 3.0)
        wedge = QPainterPath()
        wedge.arcMoveTo(outer, angle)
        wedge.arcTo(outer, angle, sweep)
        wedge.arcTo(inner, angle + sweep, -sweep)
        wedge.closeSubpath()
        selected = (i == hover)
        fill = QColor(accent) if selected else QColor(9, 28, 57)
        fill.setAlpha(min(246, alpha + 10) if selected else alpha)
        p.fillPath(wedge, fill)
        border = QColor(accent)
        border.setAlpha(255 if selected else int(105 + 95 * strength))
        p.setPen(QPen(border, 2.2 if selected else 1.25))
        p.drawPath(wedge)
        theta = math.radians(i * span)
        cx = 180 + 115 * math.sin(theta)
        cy = 180 - 115 * math.cos(theta)
        if draw_controls:
            label, icon_kind = WHEEL_LABELS.get(key, (key.replace('_', ' ').title(), 'more'))
            label = tr(label)
            _draw_action_icon(p, cx, cy - 12, icon_kind, QColor('#FFFFFF') if selected else accent.lighter(145))
            text_font = QFont('Arial', 10)
            text_font.setWeight(QFont.DemiBold if selected else QFont.Medium)
            p.setFont(text_font)
            p.setPen(QColor('#FFFFFF') if selected else QColor('#E0EEFC'))
            p.drawText(QRectF(cx - 53, cy + 5, 106, 38),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, label)
    mid_border = QColor(accent)
    mid_border.setAlpha(225)
    p.setPen(QPen(mid_border, 1.8))
    center = QColor(4, 16, 37)
    center.setAlpha(min(255, alpha + 25))
    p.setBrush(center)
    p.drawEllipse(origin, 55, 55)
    p.setPen(QColor('#D0E9FF'))
    logo_font = QFont('Arial', 13)
    logo_font.setBold(True)
    p.setFont(logo_font)
    p.drawText(QRectF(125, 140, 110, 23), Qt.AlignCenter, 'Morphix')
    p.setPen(QColor('#B8D6F4'))
    small = QFont('Arial', 9)
    p.setFont(small)
    from file_intelligence import file_summary
    for j, line in enumerate(file_summary(paths, max_lines=3)):
        p.drawText(QRectF(126, 165 + j * 14, 108, 15), Qt.AlignCenter, line)
    p.restore()


class WheelActionButton(QToolButton):
    """A *real*, independently clickable Qt button for each radial action.

    The previous version painted labels in a QWidget and tried to infer clicks
    from mouse-release coordinates. Qt/macOS could draw that overlay while
    failing to deliver releases. Child QToolButtons use Qt's native button
    clicked() semantics and remain keyboard-accessible.
    """
    def __init__(self, wheel, key, index):
        super().__init__(wheel)
        self.wheel = wheel
        self.key = key
        self.index = index
        label, pictogram = WHEEL_LABELS.get(key, (key, 'more'))
        label = tr(label)
        self.setText(label)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName('wheel_action_' + key)
        self.setAccessibleName('Morphix: ' + label)
        self.setToolTip(label)
        if key == 'rar_files':
            from core_ops import rar_writer_available
            if not rar_writer_available():
                self.setEnabled(False)
                self.setToolTip(tr('RAR needs a separately licensed RAR program. ZIP and TAR.GZ work without it.'))
        # The parent wheel draws the icons and labels.  This widget only
        # provides a real, accessible hit target.  Native macOS QToolButton
        # styling can otherwise paint an ugly square on top of the wedge.
        self.setAutoRaise(True)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.pictogram = pictogram
        self._press_handled = False
        self.refresh_style()
        self.clicked.connect(lambda _checked=False: self.wheel.invoke_action(self.key))

    def refresh_style(self):
        # Important: never paint a rectangular hover/focus background.
        # A single QPainter on WheelWindow draws EVERY visible pixel.
        self.setStyleSheet('QToolButton { background: transparent; border: 0; padding: 0; }')

    def paintEvent(self, event):
        # This QToolButton is deliberately a hit-area only.  We do not call
        # super().paintEvent(), which can draw a native macOS focus/hover square.
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            # On macOS a translucent floating Tool window can lose the
            # corresponding mouse-release when focus switches away from
            # Finder. Execute on mouse PRESS so it cannot look frozen.
            hit = self.wheel._index_at(self.mapTo(self.wheel, event.position().toPoint()))
            if 0 <= hit < len(self.wheel.actions):
                self._press_handled = True
                self.wheel.invoke_action(self.wheel.actions[hit])
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._press_handled:
            # Prevent a duplicate clicked() if the release arrives after
            # the wheel was hidden by the immediate press handler.
            self._press_handled = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.wheel.hover = self.index
        self.wheel.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.wheel.hover = -1
        self.wheel.update()
        super().leaveEvent(event)


class WheelWindow(QWidget):
    """Non-activating transparent overlay; centered at the pointer and screen-clamped."""
    action_requested = Signal(object)
    hovered = Signal(bool)
    BASE = 360
    MAX_ACTIONS = 6
    shape = 'wheel'

    def __init__(self):
        # A focusable tool panel is essential: macOS must deliver mouse clicks to Qt.
        # A macOS accessory app is hidden from the Dock, but Qt.Tool creates
        # an NSPanel that may be visible without becoming key/clickable.
        # Use a normal top-level NSWindow for the radial hit targets; keep
        # Qt.Tool on Windows so the wheel never occupies the taskbar.
        surface = Qt.Window if platform.system() == 'Darwin' else Qt.Tool
        flags = surface | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setWindowTitle('Morphix Quick Wheel')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if platform.system() == 'Darwin':
            # Tool windows otherwise hide when the user clicks Finder to add files.
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._drag_offset = None
        self._drag_start = None
        self._position_remember = False
        self.setFixedSize(290, 290)
        self.actions = []
        self.action_buttons = []
        self.profile = 'mixed'
        self.paths = []
        self.hover = -1
        self.opacity_setting = 78
        self.accent_setting = ACCENT_COLORS['Blue']
        self.glow_setting = 58
        self.at_cursor = True
        self.position = 'cursor'
        self.persistent = False
        self.show_anim = QPropertyAnimation(self, b'windowOpacity')
        self.show_anim.setDuration(115)
        self.show_anim.setEasingCurve(QEasingCurve.OutCubic)

    def set_appearance(self, size=290, opacity=78, accent='#3896FF', glow=58,
                       animation=115, position='cursor', persistent=False, **_):
        from hub_panel import POSITIONS
        self.position = position if position in POSITIONS else 'cursor'
        self.persistent = bool(persistent)
        at_cursor = self.position == 'cursor'
        size = max(220, min(440, int(size)))
        self.opacity_setting = max(25, min(95, int(opacity)))
        color = QColor(accent)
        self.accent_setting = color.name() if color.isValid() else ACCENT_COLORS['Blue']
        self.glow_setting = max(0, min(100, int(glow)))
        self.show_anim.setDuration(max(0, min(400, int(animation))))
        self.at_cursor = bool(at_cursor)
        self._position_remember = self.position == 'remember'
        # macOS keeps a native translucent backing surface. Resizing while
        # visible can leave a stale wheel visible behind the newly painted one.
        # Remove the old surface before re-creating the new-sized overlay.
        was_visible = self.isVisible()
        self.show_anim.stop()
        if was_visible:
            self.hide()
        self.setWindowOpacity(1.0)
        self.setFixedSize(size, size)
        self.relayout_buttons()
        self.update()
        if was_visible:
            self.display()

    def set_context(self, paths, profile, actions):
        self.paths = list(paths)
        self.profile = profile
        next_actions = actions[:self.MAX_ACTIONS] or ['studio']
        self.hover = -1
        # Finder selection polling can run every second. Rebuilding buttons
        # unnecessarily during mouse-down loses the matching release event.
        if next_actions != self.actions:
            self.actions = next_actions
            self.rebuild_buttons()
        self.update()

    def rebuild_buttons(self):
        for button in self.action_buttons:
            button.hide()
            button.deleteLater()
        self.action_buttons.clear()
        for index, key in enumerate(self.actions):
            button = WheelActionButton(self, key, index)
            button.show()
            self.action_buttons.append(button)
        self.relayout_buttons()

    def relayout_buttons(self):
        if not self.action_buttons:
            return
        scale = self.width() / 360.0
        for index, button in enumerate(self.action_buttons):
            theta = math.radians(index * 360.0 / len(self.action_buttons))
            cx = self.width()/2 + (115 * scale) * math.sin(theta)
            cy = self.height()/2 - (115 * scale) * math.cos(theta)
            w = round(105 * scale)
            h = round(89 * scale)
            button.setGeometry(round(cx-w/2), round(cy-h/2), w, h)
            button.refresh_style()
            button.raise_()

    def invoke_action(self, action):
        if action not in self.actions:
            return
        print(f'[Morphix] Wheel button clicked: {action}', flush=True)
        if not self.persistent:
            self.show_anim.stop()
            self.hide()
        # Dispatch after the mouse-press event has returned. This avoids
        # re-entrant modal dialogs inside the macOS mouse event handler.
        QTimer.singleShot(0, lambda a=action: self.action_requested.emit(a))

    def display(self):
        from hub_panel import place_rect, apply_shape_mask
        apply_shape_mask(self, 'ellipse', inset=max(6, self.width() // 30))
        pointer = QCursor.pos()
        prefs = QSettings('Morphix', 'Morphix')
        remembered = None
        for kx, ky in (('hub_last_x', 'hub_last_y'), ('wheel_last_x', 'wheel_last_y')):
            if prefs.contains(kx) and prefs.contains(ky):
                remembered = (int(prefs.value(kx)), int(prefs.value(ky)))
                break
        anchor = QPointF(*remembered).toPoint() if (self.position == 'remember' and remembered) else pointer
        screen = QGuiApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is None:
            return
        x, y = place_rect(self.position, self.width(), self.height(), pointer,
                          screen.availableGeometry(), remembered, margin=4)
        self.move(x, y)
        self.setWindowOpacity(0.0)
        # Only the floating wheel activates; the full Studio stays hidden.
        self.show()
        self.raise_()
        # A menu-bar accessory process can paint a Qt window without granting
        # it a key window.  Give the floating wheel focus (NOT the Studio).
        self.activateWindow()
        if platform.system() == 'Darwin':
            try:
                from AppKit import NSApplication
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
                self.raise_()
                self.activateWindow()
            except Exception as exc:
                print(f'[Morphix] Wheel activation: {exc}', flush=True)
        print(f'[Morphix] Wheel visible: {len(self.actions)} actions, '
              f'{len(self.paths)} file(s)', flush=True)
        self.show_anim.stop()
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(1.0)
        self.show_anim.start()

    def _index_at(self, pos):
        factor = self.BASE / self.width()
        dx = pos.x() * factor - 180
        dy = pos.y() * factor - 180
        radius = math.hypot(dx, dy)
        if radius < 55:
            return -2
        if radius > 158 or not self.actions:
            return -1
        angle = math.degrees(math.atan2(dx, -dy)) % 360
        step = 360.0 / len(self.actions)
        return int(((angle + step / 2) % 360) // step)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            screen = QGuiApplication.screenAt(event.globalPosition().toPoint()) or QApplication.primaryScreen()
            if screen:
                bounds = screen.availableGeometry()
                x = max(bounds.left(), min(new_pos.x(), bounds.right()-self.width()+1))
                y = max(bounds.top(), min(new_pos.y(), bounds.bottom()-self.height()+1))
                self.move(x, y)
            event.accept()
            return
        idx = self._index_at(event.position())
        if idx != self.hover:
            self.hover = idx
            self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.action_requested.emit('center_menu')
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._index_at(event.position()) == -2:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self._drag_start = event.globalPosition().toPoint()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self._drag_offset is not None:
            did_move = (event.globalPosition().toPoint() - self._drag_start).manhattanLength() > 8
            self._drag_offset = None
            self._drag_start = None
            if did_move:
                prefs=QSettings('Morphix', 'Morphix')
                prefs.setValue('hub_last_x', self.x()+self.width()//2)
                prefs.setValue('hub_last_y', self.y()+self.height()//2)
                prefs.sync()
            else:
                self.action_requested.emit('center_menu')
            event.accept()
            return
        idx = self._index_at(event.position())
        if 0 <= idx < len(self.actions):
            action = self.actions[idx]
            self.invoke_action(action)
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        new_paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        self.action_requested.emit(('add_paths', new_paths))
        event.acceptProposedAction()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.persistent:
            self.hide()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event):
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit(False)
        super().leaveEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        # Clear the *entire* translucent backing buffer before rendering.
        # Source mode replaces stale pixels, unlike the default SourceOver.
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        _render_wheel(painter, self.width(), self.actions, self.paths,
                      self.opacity_setting, self.accent_setting,
                      self.glow_setting, self.hover, draw_controls=True)
        painter.end()


def migrate_hub_settings(settings):
    """v1.6: Quick Wheel options become Action Hub options (once)."""
    if settings.contains('hub_position'):
        return
    if settings.value('wheel_remember_position', False, type=bool):
        position = 'remember'
    elif not settings.value('wheel_at_cursor', True, type=bool):
        position = 'center'
    else:
        position = 'cursor'
    settings.setValue('hub_position', position)
    if not settings.contains('hub_shape'):
        settings.setValue('hub_shape', 'wheel')
    if not settings.contains('hub_visibility'):
        settings.setValue('hub_visibility', 'shortcut')


def popup_position(px, py, width, height, sx, sy, sw, sh):
    """Center a popup near the pointer while keeping it on the active screen."""
    left = max(sx, min(int(px - width / 2), sx + max(0, sw - width)))
    top = max(sy, min(int(py - height / 2), sy + max(0, sh - height)))
    return left, top


class QuickWheelController(QObject):
    hotkey_triggered = Signal()

    def __init__(self, app, studio):
        super().__init__(app)
        self.app = app
        self.studio = studio
        self.settings = QSettings('Morphix', 'Morphix')
        migrate_hub_settings(self.settings)
        self.wheel = None
        self.current_paths = []
        self.finder_order = []
        self.thread = None
        self.worker = None
        self.hotkeys = None
        self.sticky_added = []
        self.selection_process = None
        self._finder_request = None
        self._finder_request_timer = None
        self._finder_request_reason = None
        self.monitor_finder = False
        self._empty_selection_polls = 0
        self.live_selection = QTimer(self)
        self.live_selection.setInterval(950)
        self.live_selection.timeout.connect(self.refresh_finder_live)
        self.apply_appearance()
        self.tray = QSystemTrayIcon(self._tray_icon(), app)
        self._create_tray()
        self.hotkey_triggered.connect(self.show_wheel)
        QTimer.singleShot(350, self.register_shortcut)
        QTimer.singleShot(900, self._show_persistent_hub)

    # ------------------------------------------------------------ Action Hub
    def hub_settings(self):
        st = self.settings
        return {
            'shape': str(st.value('hub_shape', 'wheel')),
            'position': str(st.value('hub_position', 'cursor')),
            'persistent': str(st.value('hub_visibility', 'shortcut')) == 'always',
            'size': st.value('wheel_size', 290),
            'opacity': st.value('wheel_opacity', 78),
            'accent': st.value('wheel_accent', ACCENT_COLORS['Blue']),
            'glow': st.value('wheel_glow', 58),
            'animation': st.value('wheel_animation', 115),
        }

    def apply_appearance(self):
        """(Re)build the hub window when the shape changes; restyle otherwise."""
        cfg = self.hub_settings()
        shape = cfg.pop('shape')
        if self.wheel is None or self.wheel.shape != shape:
            old = self.wheel
            if shape == 'wheel':
                hub = WheelWindow()
            else:
                from hub_panel import PanelWindow
                hub = PanelWindow(shape)
            hub.action_requested.connect(self.action_selected)
            hub.hovered.connect(self._hub_hovered)
            self.wheel = hub
            if old is not None:
                old.hide()
                old.deleteLater()
        self.wheel.set_appearance(**cfg)
        if self.current_paths or cfg['persistent']:
            self._set_context(self.current_paths)
        if cfg['persistent']:
            QTimer.singleShot(50, self._show_persistent_hub)
        elif not self.current_paths:
            self.wheel.hide()

    def _persistent(self):
        return bool(getattr(self.wheel, 'persistent', False))

    def _show_persistent_hub(self):
        if self._persistent() and not self.wheel.isVisible():
            self._set_context(self.current_paths)
            self.wheel.display()

    def _hub_hovered(self, inside):
        """Always-visible hub: pick up the Finder selection when the mouse arrives."""
        if not self._persistent():
            return
        if inside:
            self.monitor_finder = True
            if platform.system() == 'Darwin':
                self._read_finder_selection('hover')
            else:
                self.refresh_selection_now()
            self.live_selection.start()
        else:
            self.live_selection.stop()

    def _dismiss_hub(self):
        if not self._persistent():
            self.live_selection.stop()
            self.wheel.show_anim.stop()
            self.wheel.hide()

    def _tray_icon(self):
        # Unlike the detailed launcher icon, this monochrome-heavy M stays
        # recognizable at 18x18 in the macOS menu bar, light or dark mode.
        img = QPixmap(64, 64)
        img.fill(Qt.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#288FF0'))
        painter.drawRoundedRect(3, 3, 58, 58, 18, 18)
        painter.setFont(QFont('Arial', 39, QFont.Bold))
        painter.setPen(QColor('#FFFFFF'))
        painter.drawText(img.rect(), Qt.AlignCenter, 'M')
        painter.end()
        return QIcon(img)

    def _create_tray(self):
        self.tray_menu = QMenu()
        menu = self.tray_menu
        status = menu.addAction(tr('Morphix  ·  Running in background'))
        status.setEnabled(False)
        self.job_status_action = menu.addAction('')
        self.job_status_action.setEnabled(False)
        self.job_status_action.setVisible(False)
        self.job_cancel_action = menu.addAction(tr('Cancel current task'), self.cancel_job)
        self.job_cancel_action.setVisible(False)
        menu.addSeparator()
        # Dispatch AFTER the native NSMenu is dismissed. Re-entrant native
        # menu callbacks could prevent a child window/file chooser activating.
        self.hub_menu_action = menu.addAction(self._hub_menu_text(),
                       lambda: self._after_tray_menu(self.show_wheel))
        menu.addAction(tr('Choose files for the Action Hub…'), lambda: self._after_tray_menu(self.test_wheel))
        menu.addAction(tr('Simple actions menu · Choose files…'), lambda: self._after_tray_menu(self.test_safe_menu))
        menu.addSeparator()
        menu.addAction(tr('Open Morphix Studio'), lambda: self._after_tray_menu(self.open_studio))
        menu.addAction(tr('Settings…'), lambda: self._after_tray_menu(self.open_preferences))
        menu.addAction(tr('Add-ons…'), lambda: self._after_tray_menu(lambda: self.open_preferences(page=4)))
        menu.addAction(tr('Hide the Action Hub'), self.hide_wheel)
        from i18n import amp
        help_menu = menu.addMenu(amp(tr('Help & diagnostics')))
        help_menu.addAction(tr('Check the Finder selection'), lambda: self._after_tray_menu(self.test_selection))
        help_menu.addAction(tr('Status of conversion engines'), lambda: self._after_tray_menu(self.show_engine_status))
        if platform.system() == 'Darwin':
            from native_hotkeys import open_accessibility_settings
            help_menu.addAction(tr('Shortcut not working? Allow access…'), open_accessibility_settings)
        help_menu.addAction(tr('Reset the Action Hub appearance'), self.reset_wheel_appearance)
        menu.addSeparator()
        menu.addAction(tr('Quit Morphix'), self.quit_app)
        menu.aboutToShow.connect(lambda: None if self._persistent() else self.hide_wheel())
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(tr('Morphix · Select files, then press your shortcut'))
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _after_tray_menu(self, callback):
        """Avoid opening Qt windows inside a native macOS status-menu callback."""
        QTimer.singleShot(80, callback)

    def _tray_activated(self, reason):
        # macOS status items with an attached NSMenu may emit Trigger when the
        # MENU opens. Opening the wheel at the same time places an unclickable
        # overlay BEHIND the native menu (exactly the reported screenshot).
        # On macOS the wheel is opened by the explicit menu item or shortcut.
        if platform.system() == 'Darwin':
            return
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            # Windows convention: clicking the tray icon opens the app window.
            # The Action Hub has its shortcut and its own menu entry.
            self._after_tray_menu(self.open_studio)

    def _hub_menu_text(self):
        from shortcut_logic import display_shortcut
        combo = str(self.settings.value('shortcut', DEFAULT_SHORTCUT))
        return tr('Show the Action Hub') + '   ' + display_shortcut(combo, platform.system() == 'Darwin')

    def notify(self, title, message):
        if self.tray.isVisible() and self.tray.supportsMessages():
            self.tray.showMessage(title, message, QSystemTrayIcon.Information, 4500)
        print(f'[{title}] {message}')

    def register_shortcut(self):
        if self.hotkeys:
            try:
                self.hotkeys.stop()
            except Exception:
                pass
            self.hotkeys = None
        shortcut = str(self.settings.value('shortcut', DEFAULT_SHORTCUT))
        if getattr(self, 'hub_menu_action', None) is not None:
            self.hub_menu_action.setText(self._hub_menu_text())
        try:
            if platform.system() == 'Darwin':
                # Never use pynput's macOS listener thread. Apple's text-input
                # APIs may assert when called from a non-main dispatch queue.
                from native_hotkeys import MacGlobalHotkey
                self.hotkeys = MacGlobalHotkey(shortcut, self.hotkey_triggered.emit)
            elif platform.system() == 'Linux':
                import linux_hotkeys
                self.hotkeys = linux_hotkeys.create(shortcut, self.hotkey_triggered.emit)
                try:
                    self.hotkeys.start()
                except RuntimeError as exc:
                    if str(exc) not in ('NO_X11', 'ALREADY_REGISTERED'):
                        raise
                    # Wayland, or the key is taken on X11: let the desktop run `Morphix --hotkey`.
                    self.hotkeys = linux_hotkeys.DesktopShortcut(shortcut, self.hotkey_triggered.emit)
                    try:
                        self.hotkeys.start()
                    except RuntimeError:
                        if str(exc) == 'ALREADY_REGISTERED':
                            raise exc
                        raise RuntimeError('MANUAL_SHORTCUT')
            else:
                from windows_hotkeys import WindowsGlobalHotkey
                self.hotkeys = WindowsGlobalHotkey(shortcut, self.hotkey_triggered.emit)
            if platform.system() != 'Linux':
                self.hotkeys.start()
            print(f'[Morphix] Hotkey monitor installed: {shortcut} '
                  f'({getattr(self.hotkeys, "mode", None) or "permission may still be required"}).', flush=True)
            if platform.system() == 'Darwin':
                QTimer.singleShot(600, self._check_shortcut_permission)
        except Exception as exc:
            self.hotkeys = None
            if 'ALREADY_REGISTERED' in str(exc):
                from shortcut_logic import display_shortcut
                message = tr('Another program already uses {keys}. Choose a different shortcut in Settings → Keyboard shortcut.',
                             keys=display_shortcut(shortcut, False))
            elif 'MANUAL_SHORTCUT' in str(exc):
                from linux_integration import manual_shortcut_command
                message = tr('Add a keyboard shortcut in your system settings that runs: {cmd}',
                             cmd=manual_shortcut_command())
            else:
                message = f'{exc}. ' + tr('Use the Morphix menu instead.')
            print(f'[Morphix] Shortcut unavailable: {exc}', flush=True)
            self.notify(tr('Shortcut unavailable'), message)

    def _check_shortcut_permission(self):
        """Without Accessibility permission macOS silently drops every key press."""
        from native_hotkeys import accessibility_trusted
        state = accessibility_trusted(prompt=False)
        print(f'[Morphix] Accessibility permission: {state}', flush=True)
        if state is not False:
            return
        accessibility_trusted(prompt=True)          # macOS shows its own sheet
        self.notify(tr('Morphix · Allow the shortcut'),
                    tr('System Settings → Privacy & Security → Accessibility → turn on Morphix.'))
        if getattr(self, '_permission_timer', None) is None:
            self._permission_timer = QTimer(self)
            self._permission_timer.setInterval(2000)
            self._permission_timer.timeout.connect(self._poll_shortcut_permission)
        self._permission_timer.start()

    def _poll_shortcut_permission(self):
        from native_hotkeys import accessibility_trusted
        if accessibility_trusted(prompt=False):
            self._permission_timer.stop()
            print('[Morphix] Accessibility granted; re-registering shortcut.', flush=True)
            # A monitor created before the grant can stay deaf; recreate it.
            QTimer.singleShot(0, self.register_shortcut)
            self.notify('Morphix', tr('Shortcut is ready. Select files in Finder and press it.'))

    def test_wheel(self):
        # End-to-end overlay test independent of Finder privacy permission or
        # macOS global shortcut -- crucial when troubleshooting first launch.
        paths, _ = QFileDialog.getOpenFileNames(None, tr('Choose files for the Action Hub'))
        if paths:
            self.show_wheel(paths_override=paths)

    def test_safe_menu(self):
        """Real Qt menu fallback, independent of translucent-wheel hit testing."""
        paths, _ = QFileDialog.getOpenFileNames(None, tr('Choose files for Morphix actions'))
        if paths:
            self.show_safe_menu(paths)

    def show_safe_menu(self, paths):
        paths = [str(p) for p in dict.fromkeys(paths) if Path(p).is_file()]
        if not paths:
            self.notify('Morphix', tr('No files selected.'))
            return
        self.sticky_added = []
        self._set_context(paths)
        from main import ACTIONS, supported_actions
        options = supported_actions(paths)
        menu = QMenu()
        from file_intelligence import file_summary
        summary = menu.addAction('  ·  '.join(file_summary(paths)))
        summary.setEnabled(False)
        menu.addSeparator()
        for key in options:
            from i18n import amp
            item = menu.addAction(amp(tr(ACTIONS.get(key, key))))
            if key == 'rar_files':
                from core_ops import rar_writer_available
                item.setEnabled(rar_writer_available())
            item.triggered.connect(lambda _checked=False, selected=key: self.action_selected(selected))
        menu.addSeparator()
        menu.addAction(tr('Open Morphix Studio'), self.open_studio)
        menu.exec(QCursor.pos())

    def test_selection(self):
        if platform.system() == 'Darwin':
            self._read_finder_selection('diagnostic')
            return
        try:
            self._show_selection_diagnostic(get_explorer_selection())
        except Exception as exc:
            QMessageBox.warning(None, tr('Morphix · Finder selection'), str(exc))

    def _show_selection_diagnostic(self, paths):
        detail = (tr('Found {n} file(s):', n=len(paths)) + '\n' +
                  '\n'.join(Path(p).name for p in paths[:12])) if paths else tr(
                  'No selected files were found.\n\nSelect one or more files in a Finder window, '
                  'then press your shortcut. macOS may ask for permission under '
                  'Privacy & Security → Automation.')
        QMessageBox.information(None, tr('Morphix · Finder selection'), detail)

    def show_engine_status(self):
        from ocr_engine import find_tessdata
        from office_engine import find_office_engine
        from core_ops import rar_writer_available
        ready = tr('Ready')
        rows = [
            (tr('PDF & images'), ready),
            (tr('Arabic + English OCR'), ready if find_tessdata() else tr('Language data missing')),
            (tr('Office → PDF'), ready if find_office_engine() else tr('Needs LibreOffice')),
            (tr('Speech → Text (offline)'), _speech_status()),
            (tr('ZIP and TAR.GZ'), ready),
            (tr('RAR creation'), tr('Licensed RAR program found') if rar_writer_available()
                                  else tr('Needs a separately licensed RAR program')),
        ]
        status = '<br>'.join(f'<b>{a}:</b> {b}' for a, b in rows)
        QMessageBox.information(None, tr('Morphix · Conversion engines'), status)

    def show_welcome(self):
        # This compact launcher now appears on every explicit interactive
        # launch (unless --background/--studio/--settings/--test-wheel is used).
        # Previous versions stored a persistent one-time flag that made the
        # app appear unresponsive on later launches.
        box = QDialog(None)
        box.setWindowTitle(tr('Morphix · Ready'))
        box.setWindowIcon(self._tray_icon())
        box.setFixedWidth(470)
        box.setStyleSheet('''
            QDialog { background: #08182D; color: #EAF5FF; }
            QLabel { color: #DEEFFF; background: transparent; }
            QLabel#subtle { color: #9BBDE1; font-size: 12px; }
            QPushButton { color: #F1F7FF; background: #152D4C; border: 1px solid #3B6799;
              border-radius: 10px; padding: 12px 14px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #1E4673; border-color: #66AAFA; }
            QPushButton#main { background: #2379E2; border-color: #62ACFF; }
        ''')
        layout = QVBoxLayout(box)
        layout.setContentsMargins(27, 26, 27, 27)
        layout.setSpacing(13)
        title = QLabel(tr('Morphix is running'))
        title.setStyleSheet('color: #9BD1FF; font-size: 23px; font-weight: 800;')
        layout.addWidget(title)
        info = QLabel(tr('Morphix keeps running in the background after you close Studio. '
                         'Look for the blue M in the menu bar.'))
        info.setWordWrap(True)
        layout.addWidget(info)
        hint = QLabel(tr('1. Select files in Finder.\n2. Press your shortcut to open the Action Hub.\n'
                         '3. Use the blue M menu for settings, or to quit.'))
        hint.setObjectName('subtle')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        def choice(callback):
            box.accept()
            QTimer.singleShot(0, callback)
        quick = QPushButton(tr('Try the Action Hub with files…'))
        quick.setObjectName('main')
        quick.clicked.connect(lambda: choice(self.test_wheel))
        safe_menu = QPushButton(tr('Simple actions menu · Choose files…'))
        safe_menu.clicked.connect(lambda: choice(self.test_safe_menu))
        settings_button = QPushButton(tr('Settings…'))
        settings_button.clicked.connect(lambda: choice(self.open_preferences))
        studio = QPushButton(tr('Open Morphix Studio'))
        studio.clicked.connect(lambda: choice(self.open_studio))
        dismiss = QPushButton(tr('Keep running in the background'))
        dismiss.clicked.connect(box.accept)
        for button in (quick, safe_menu, settings_button, studio, dismiss):
            layout.addWidget(button)
        box.exec()

    def _read_finder_selection(self, reason='wheel'):
        """Read Finder without blocking Qt's native menu/overlay event loop.

        `subprocess.run(['osascript', ...], timeout=10)` used to run directly in
        the GUI callback; a Finder Automation permission prompt could make
        Morphix look completely frozen. QProcess + a deadline avoids it.
        """
        if self._finder_request is not None:
            # Do not create overlapping osascript processes while a permission
            # sheet is open. The newest request wins if it is a diagnosis.
            if reason == 'diagnostic':
                self._finder_request_reason = reason
            return
        self._finder_request_reason = reason
        proc = QProcess(self)
        timer = QTimer(self)
        timer.setSingleShot(True)
        self._finder_request = proc
        self._finder_request_timer = timer
        script = '''tell application "Finder"
            set chosen to selection
            set collected to ""
            repeat with itemRef in chosen
                try
                    set collected to collected & POSIX path of (itemRef as alias) & (ASCII character 10)
                end try
            end repeat
            return collected
        end tell'''
        proc.finished.connect(lambda code, status, p=proc: self._finder_request_finished(p))
        timer.timeout.connect(lambda p=proc: self._finder_request_timeout(p))
        timer.start(6500)
        proc.start('osascript', ['-e', script])
        print('[Morphix] Reading Finder selection asynchronously…', flush=True)

    def _clear_finder_request(self, proc):
        if self._finder_request is not proc:
            return None
        timer = self._finder_request_timer
        if timer:
            timer.stop()
            timer.deleteLater()
        self._finder_request_timer = None
        self._finder_request = None
        reason = self._finder_request_reason
        self._finder_request_reason = None
        proc.deleteLater()
        return reason

    def _finder_request_timeout(self, proc):
        if proc is not self._finder_request:
            return
        # Interrupt only the hung Finder selection subprocess, never the GUI.
        proc.kill()
        self._clear_finder_request(proc)
        self.notify(tr('Morphix · Finder selection'),
                    tr('Finder did not answer. Check the Automation permission for Morphix.'))

    def _finder_request_finished(self, proc):
        if proc is not self._finder_request:
            return
        reason = self._clear_finder_request(proc)
        stdout = bytes(proc.readAllStandardOutput()).decode('utf-8', 'replace')
        stderr = bytes(proc.readAllStandardError()).decode('utf-8', 'replace')
        if proc.exitCode() != 0:
            print('[Morphix] Finder selection failed:', stderr.strip(), flush=True)
            if reason != 'hover':
                self.notify(tr('Morphix · Finder selection'),
                            (stderr.strip() or tr('Finder selection unavailable'))[:240])
            return
        paths = [line for line in stdout.splitlines() if Path(line).is_file()]
        if reason == 'diagnostic':
            self._show_selection_diagnostic(paths)
        elif paths:
            self._display_finder_wheel(paths)
        elif reason == 'hover':
            pass
        elif self._persistent():
            self._set_context(list(self.sticky_added))
            self.wheel.raise_()
        else:
            self.notify('Morphix', tr('Select one or more files in Finder, then try again.'))

    def _display_finder_wheel(self, paths):
        """Rebuild the live Finder wheel after the asynchronous result arrives."""
        from file_intelligence import preserve_selected_order
        self._empty_selection_polls = 0
        self.sticky_added = []
        self.monitor_finder = True
        self.finder_order = preserve_selected_order(self.finder_order, paths)
        self._set_context(list(dict.fromkeys(self.finder_order + self.sticky_added)))
        if not self.wheel.isVisible():
            self.wheel.display()
        else:
            self.wheel.raise_()
            self.wheel.activateWindow()
        self.live_selection.start()

    def show_wheel(self, use_studio_selection=False, paths_override=None):
        if platform.system() == 'Darwin' and paths_override is None and not use_studio_selection:
            if self._persistent() and self.wheel.isVisible():
                self.wheel.raise_()
            self._read_finder_selection('wheel')
            return
        if self.wheel.isVisible():
            # Refresh selections on repeat shortcut, instead of silently hiding the wheel.
            if paths_override is not None:
                self.sticky_added = []
                self._set_context(list(paths_override))
            elif not use_studio_selection:
                self.refresh_selection_now()
            else:
                self.sticky_added = []
                self._set_context(self.studio.selected_paths())
            self.wheel.raise_()
            return
        try:
            if paths_override is not None:
                paths = list(paths_override)
            else:
                paths = self.studio.selected_paths() if use_studio_selection else get_explorer_selection()
        except Exception as exc:
            self.notify(tr('Morphix · Finder selection'), str(exc))
            paths = []
        paths = [p for p in dict.fromkeys(paths) if Path(p).is_file()]
        if not paths:
            if self._persistent():
                self._set_context([])
                self.wheel.display()
            elif use_studio_selection:
                self.notify('Morphix', tr('Select one or more files in Studio first.'))
            else:
                self.notify('Morphix', tr('Select one or more files in Finder, then try again.'))
            return
        self.sticky_added = []
        self._empty_selection_polls = 0
        # Explicit file-picker previews must not unexpectedly absorb old Finder
        # selection. Only a Finder-launched wheel polls changes in Finder.
        self.monitor_finder = paths_override is None and not use_studio_selection
        self.finder_order = list(paths) if self.monitor_finder else []
        self._set_context(paths)
        self.wheel.display()
        if self.monitor_finder:
            self.live_selection.start()
        else:
            self.live_selection.stop()

    def _set_context(self, paths):
        from main import supported_actions
        paths = [str(p) for p in dict.fromkeys(paths) if Path(p).is_file()]
        if not paths:
            self.current_paths = []
            if self._persistent():
                self.wheel.set_context([], 'mixed', [] if self.wheel.shape != 'wheel' else ['studio'])
            else:
                self.wheel.hide()
                self.live_selection.stop()
            return
        self.current_paths = paths
        profile = selection_profile(paths)
        allowed = set(supported_actions(paths))
        # Old settings contained obsolete 'studio' entries; v0.9 starts new defaults.
        try:
            config = json.loads(self.settings.value('wheel_v14/' + profile, 'null'))
        except (ValueError, TypeError):
            config = None
        defaults = PROFILES[profile][1]
        candidates = config if isinstance(config, list) else defaults
        # Give existing users the newly added actions once (they can remove them).
        for new_key, flag in (('transcribe_media', 'wheel_v15_transcribe/'), ('ocr_searchable_pdf', 'wheel_v16_ocr/'),
                              ('organize_pdf', 'wheel_v19_organize/'), ('sign_pdf', 'wheel_v19_sign/'),
                              ('sign_images', 'wheel_v19_sign/'), ('ppt_media', 'wheel_v19_ppt/'),
                              ('heic_jpg', 'wheel_v19_heic/')):
            if (isinstance(config, list) and new_key in allowed and new_key not in candidates
                    and not self.settings.value(flag + profile, False, type=bool)):
                candidates = [new_key] + list(candidates)[:7]
                self.settings.setValue('wheel_v14/' + profile, json.dumps(candidates))
                self.settings.setValue(flag + profile, True)
        # v0.9 mixed profile stored only ZIP/RAR; add the new working TAR.GZ
        # option on upgrade without discarding other personalization.
        if profile == 'mixed' and candidates == ['zip_files', 'rar_files']:
            candidates = ['zip_files', 'tar_gz_files', 'rar_files']
        actions = [key for key in candidates if key in allowed or (key == 'more_actions' and profile != 'mixed')]
        if not actions:
            actions = ['zip_files'] if profile == 'mixed' else [key for key in defaults if key in allowed]
        self.wheel.set_context(paths, profile, actions[:self.wheel.MAX_ACTIONS])

    def refresh_finder_live(self):
        """Non-blocking Finder polling: the wheel updates when selection changes."""
        if not self.wheel.isVisible() or not self.monitor_finder:
            self.live_selection.stop()
            return
        if platform.system() == 'Darwin':
            if self.selection_process is not None:
                return
            proc = QProcess(self)
            self.selection_process = proc
            script = '''tell application "Finder"
                set chosen to selection
                set collected to ""
                repeat with itemRef in chosen
                    try
                        set collected to collected & POSIX path of (itemRef as alias) & (ASCII character 10)
                    end try
                end repeat
                return collected
            end tell'''
            proc.finished.connect(lambda _code, _status: self._finder_polled(proc))
            QTimer.singleShot(6500, lambda p=proc: self._expire_finder_poll(p))
            proc.start('osascript', ['-e', script])
        elif platform.system() == 'Windows':
            try:
                paths = get_explorer_selection()
                if paths:
                    self._empty_selection_polls = 0
                    from file_intelligence import preserve_selected_order
                    self.finder_order = preserve_selected_order(self.finder_order, paths)
                    self._set_context(list(dict.fromkeys(self.finder_order + self.sticky_added)))
                else:
                    self._empty_selection_polls += 1
                    if self._empty_selection_polls >= 2:
                        self.finder_order = []
                        self._set_context(list(self.sticky_added))
            except Exception:
                pass

    def _expire_finder_poll(self, proc):
        if self.selection_process is proc:
            print('[Morphix] Finder live-poll timed out; canceling osascript.', flush=True)
            proc.kill()

    def _finder_polled(self, proc):
        try:
            if proc.exitCode() == 0 and self.wheel.isVisible():
                paths = [line.strip() for line in bytes(proc.readAllStandardOutput()).decode('utf-8', 'replace').splitlines()]
                paths = [p for p in paths if Path(p).is_file()]
                if paths:
                    self._empty_selection_polls = 0
                    # Finder selection REPLACES previous Finder items. Explicit
                    # Add More / drag-and-drop items remain sticky by choice.
                    from file_intelligence import preserve_selected_order
                    self.finder_order = preserve_selected_order(self.finder_order, paths)
                    combined = list(dict.fromkeys(self.finder_order + self.sticky_added))
                    if combined != self.current_paths:
                        self._set_context(combined)
                else:
                    self._empty_selection_polls += 1
                    # Ignore a single empty transient during Finder focus changes.
                    if self._empty_selection_polls >= 2:
                        self.finder_order = []
                        combined = list(self.sticky_added)
                        if combined != self.current_paths:
                            self._set_context(combined)
        finally:
            proc.deleteLater()
            if self.selection_process is proc:
                self.selection_process = None

    def add_more_files(self):
        paths, _ = QFileDialog.getOpenFileNames(None, tr('Add files to the selection'))
        if paths:
            self.sticky_added = list(dict.fromkeys(self.sticky_added + paths))
            self._set_context(self.current_paths + paths)
            if not self.wheel.isVisible(): self.wheel.display()

    def refresh_selection_now(self):
        if platform.system() == 'Darwin':
            self._read_finder_selection('wheel')
            return
        try:
            paths = get_explorer_selection()
            self._empty_selection_polls = 0 if paths else self._empty_selection_polls + 1
            self._set_context(list(dict.fromkeys(paths + self.sticky_added)))
        except Exception as exc: self.notify(tr('Morphix · Finder selection'), str(exc))

    def clear_selection(self):
        self.sticky_added = []
        self.current_paths = []
        self.finder_order = []
        if self._persistent():
            self._set_context([])
        else:
            self.wheel.hide()
            self.live_selection.stop()
        self.notify('Morphix', tr('Selection cleared. Choose new files to continue.'))

    def action_selected(self, action):
        if isinstance(action, tuple) and action[0] == 'add_paths':
            additions = [p for p in action[1] if Path(p).is_file()]
            self.sticky_added = list(dict.fromkeys(self.sticky_added + additions))
            self._set_context(self.current_paths + additions)
            return
        if action == 'center_menu':
            menu = QMenu()
            menu.addAction(tr('Add more files…'), self.add_more_files)
            menu.addAction(tr('Refresh Finder selection'), self.refresh_selection_now)
            menu.addAction(tr('Clear selection'), self.clear_selection)
            menu.addSeparator()
            menu.addAction(tr('Settings…'), self.open_preferences)
            menu.addAction(tr('Open Morphix Studio'), self.open_studio)
            menu.addAction(tr('Hide the Action Hub'), self.hide_wheel)
            menu.exec(QCursor.pos())
            return
        if action == 'hide_hub':
            self.hide_wheel()
            return
        if action == 'more_actions':
            from main import supported_actions, ACTIONS
            menu = QMenu()
            for key in supported_actions(self.current_paths):
                if key not in self.wheel.actions:
                    from i18n import amp
                    menu.addAction(amp(tr(ACTIONS.get(key, key))), lambda checked=False, k=key: self.action_selected(k))
            if not self.current_paths:
                menu.addAction(tr('Choose files for the Action Hub…'), self.add_more_files)
            menu.addSeparator()
            menu.addAction(tr('Open Morphix Studio'), lambda: self.open_studio(self.current_paths or None))
            menu.exec(QCursor.pos())
            return
        if action == 'studio':
            # Studio is for customization and bulk management, not a required
            # detour before cropping or rotating a single picture.
            self._dismiss_hub()
            self.open_studio(self.current_paths or None)
            return
        if action in ('visual_pdf', 'visual_image'):
            paths = list(self.current_paths)
            self._dismiss_hub()
            if not paths:
                self.notify('Morphix', tr('Select a file first.'))
                return
            try:
                from visual_editor import PdfEditor, QuickImageEditor
                editor = (QuickImageEditor(paths[0]) if action == 'visual_image'
                          else PdfEditor(paths[0]))
                # Top-level modal editor near the pointer; Studio stays hidden.
                screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
                if screen:
                    bounds = screen.availableGeometry()
                    x, y = popup_position(QCursor.pos().x(), QCursor.pos().y(),
                                          editor.width(), editor.height(),
                                          bounds.x(), bounds.y(), bounds.width(), bounds.height())
                    editor.move(x, y)
                editor.exec()
            except Exception as exc:
                import traceback
                print('[Morphix] Quick editor failed:\n' + traceback.format_exc(), flush=True)
                QMessageBox.warning(None, tr('Morphix · Editor unavailable'),
                    f'{exc}\n\n' + tr('Run Launch_Morphix_Mac.command again to repair the installation.'))
            return
        if self.thread is not None:
            self.notify(tr('Morphix is busy'), tr('Wait for the current task to finish, or cancel it from the M menu.'))
            return
        from main import ACTIONS
        paths = list(self.current_paths)
        if not paths:
            self.notify('Morphix', tr('Select one or more files in Finder, then try again.'))
            return
        self._dismiss_hub()
        if action in ('merge_pdf', 'merge_optimize', 'images_pdf', 'docs_merge_pdf', 'xlsx_merge') and len(paths) > 1:
            from merge_order_dialog import ask_merge_order
            ordered = ask_merge_order(paths)
            if ordered is None:
                self.wheel.display()
                if self.monitor_finder:
                    self.live_selection.start()
                return
            paths = ordered
        options = {}
        if action in ('split_pdf', 'separate_pdf'):
            try:
                from range_dialogs import ask_pdf_ranges
                ranges = ask_pdf_ranges(paths, separate=(action == 'separate_pdf'))
            except Exception as exc:
                QMessageBox.warning(None, tr('Morphix · PDF tools unavailable'),
                    f'{exc}\n\n' + tr('Run Launch_Morphix_Mac.command again to repair the installation.'))
                return
            if ranges is None:
                self.wheel.display()
                if self.monitor_finder: self.live_selection.start()
                return
            options['page_ranges'] = ranges
        if action in ('image_compress', 'optimize_pdf', 'merge_optimize'):
            from compression_dialog import CompressionDialog
            dialog = CompressionDialog(paths, 'image' if action == 'image_compress' else 'pdf')
            if not dialog.exec():
                self.wheel.display()
                if self.monitor_finder:
                    self.live_selection.start()
                return
            options = dialog.options()
        if action == 'remove_bg':
            from background_dialog import ask_background_options
            chosen = ask_background_options(paths)
            if chosen is None:
                return
            options = chosen
        if action == 'transcribe_media':
            from transcription_dialog import ask_transcription_options
            chosen = ask_transcription_options(paths)
            if chosen is None:
                return
            options = chosen
        try:
            from action_dialogs import ask_action_options
            extra = ask_action_options(action, paths)
        except Exception as exc:
            QMessageBox.warning(None, tr('Morphix'), str(exc))
            return
        if extra is None:
            return
        options.update(extra)
        parents = {str(Path(p).parent) for p in paths}
        folder = next(iter(parents)) if len(parents) == 1 else str(Path.home() / 'Documents' / 'Morphix Output')
        Path(folder).mkdir(parents=True, exist_ok=True)
        from conversion_job import ConversionJob
        self.thread = ConversionJob(action, paths, folder, options, parent=self)
        self.worker = None
        self._job_label = tr(ACTIONS.get(action, action))
        self.thread.completed.connect(self.finished_action)
        self.thread.failed.connect(self.failed_action)
        self.thread.finished.connect(self.cleanup)
        self.thread.progress.connect(self._job_progress)
        self.thread.status.connect(self._job_status)
        self.thread.start()
        self._set_job_menu(f'{self._job_label} · 0%')
        self.notify('Morphix', tr('Working on: {task}…', task=self._job_label))

    def _set_job_menu(self, text):
        running = text is not None
        self.job_status_action.setVisible(running)
        self.job_cancel_action.setVisible(running)
        if running:
            self.job_status_action.setText(text)
            self.tray.setToolTip('Morphix · ' + text)
        else:
            self.tray.setToolTip(tr('Morphix · Select files, then press your shortcut'))

    def _job_progress(self, value):
        self._job_percent = int(value)
        self._set_job_menu(f'{self._job_label} · {self._job_percent}%')

    def _job_status(self, text):
        self._set_job_menu(f'{getattr(self, "_job_percent", 0)}% · {text}'[:110])

    def cancel_job(self):
        if self.thread is not None:
            self.thread.cancel()

    def finished_action(self, outputs):
        self.notify(tr('Morphix · Done'), tr('{n} file(s) saved next to the originals.', n=len(outputs)))
        if outputs:
            self.last_output_dir = Path(outputs[0]).parent
            for file in outputs[:12]:
                print(f'[Morphix] Saved: {Path(file)}', flush=True)

    def failed_action(self, error):
        if error.strip() == 'Cancelled.':
            self.notify('Morphix', tr('Cancelled. Speech → Text continues where it stopped next time you run it on the same file.'))
            return
        from main import _friendly_error
        message = _friendly_error(error)
        self.notify(tr('Morphix · Something went wrong'), message[:300])
        QMessageBox.warning(None, tr('Morphix · The task could not be completed'), message[:1500])
        # Failures must be visible; previously notification-only looked like a dead wheel.

    def cleanup(self):
        job = self.thread
        self.thread = None
        self.worker = None
        self._set_job_menu(None)
        if job is not None:
            job.deleteLater()

    def open_studio(self, selected=None, page=None):
        print('[Morphix] Open Studio requested from background menu', flush=True)
        # Only one process owns the floating wheel; an independent process owns
        # the desktop Studio. Hide the wheel before requesting the Studio.
        self._cancel_pending_finder_request()
        self._dismiss_hub()
        from studio_host import send_to_studio, start_studio_process, allow_foreground
        allow_foreground()
        command = 'preferences' if page is not None else 'raise'
        if send_to_studio(selected, command=command, page=page or 0):
            return
        try:
            process = start_studio_process(sys.executable, Path(__file__).resolve().parent / 'main.py',
                                           frozen=bool(getattr(sys, 'frozen', False)),
                                           paths=selected, command=command, page=page or 0)
            # QProcess.startDetached used to report success even when Cocoa
            # crashed immediately. Show a clear diagnostic if Studio exits.
            QTimer.singleShot(1400, lambda p=process: self._check_studio_launch(p))
        except Exception as exc:
            self.notify('Morphix Studio', str(exc))

    def restart_for_language(self):
        """Start a fresh Morphix in the newly chosen language, then quit this one."""
        if getattr(self, '_restarting', False):
            return
        self._restarting = True
        if self.thread is not None:
            self.thread.cancel()
        self._cancel_pending_finder_request()
        if self.hotkeys:
            try:
                self.hotkeys.stop()
            except Exception:
                pass
        self.tray.hide()
        self.wheel.hide()
        server = getattr(self, 'instance_server', None)
        if server is not None:
            server.close()          # free the single-instance socket for the new process
        import i18n
        i18n.spawn_relaunch(delay=1.3)
        QTimer.singleShot(150, self.app.quit)

    def _check_studio_launch(self, process):
        status = process.poll()
        if status is not None and status != 0:
            import platform
            if platform.system() == 'Darwin':
                logfile = str(Path.home() / 'Library' / 'Logs' / 'Morphix' / 'studio.log')
            else:
                logfile = 'Morphix Studio log'
            msg = tr('Studio could not start (code {code}). Details: {log}', code=status, log=logfile)
            print('[Morphix Studio] ' + msg, flush=True)
            self.notify('Morphix Studio', msg)

    def on_studio_hidden(self):
        # No AppKit activation-policy flips inside the background process.
        pass

    def open_preferences(self, page=0):
        # Keep ALL modals out of the always-on AppKit accessory process.
        # Settings open inside the dedicated, normal Studio process.
        self.open_studio(page=page)

    def studio_shortcut_label(self):
        from shortcut_logic import display_shortcut
        combo = str(self.settings.value('shortcut', DEFAULT_SHORTCUT))
        return tr('Select files anywhere, then press') + ' ' + display_shortcut(combo, platform.system() == 'Darwin')

    def hide_wheel(self):
        self.wheel.hide()
        self.live_selection.stop()
        self.monitor_finder = False
        # A late Finder response should not resurrect a dismissed wheel.
        self._cancel_pending_finder_request()

    def _cancel_pending_finder_request(self):
        proc = self._finder_request
        if proc is not None:
            proc.kill()
            self._clear_finder_request(proc)

    def reset_wheel_appearance(self):
        for key in ('wheel_size', 'wheel_opacity', 'wheel_accent',
                    'wheel_glow', 'wheel_animation', 'wheel_at_cursor',
                    'wheel_remember_position', 'wheel_last_x', 'wheel_last_y',
                    'hub_shape', 'hub_position', 'hub_visibility', 'hub_last_x', 'hub_last_y'):
            self.settings.remove(key)
        self.settings.sync()
        self.apply_appearance()
        self.notify('Morphix', tr('The Action Hub appearance was reset to its defaults.'))

    def quit_app(self):
        if self.thread is not None:
            answer = QMessageBox.question(None, tr('Morphix · A task is running'),
                tr('A task is still running. Cancel it and quit?\n\n'
                   'Speech → Text keeps its progress and continues next time.'))
            if answer != QMessageBox.Yes:
                return
            self.thread.cancel()
        self._cancel_pending_finder_request()
        if self.selection_process is not None:
            self.selection_process.kill()
        if self.hotkeys:
            self.hotkeys.stop()
        self.tray.hide()
        self.app.quit()
