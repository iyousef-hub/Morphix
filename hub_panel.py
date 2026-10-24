"""Action Hub panels: square / rectangle / bar (the wheel lives in quickwheel.py).

The visible content (PanelContent) is a plain widget so the very same code is
used on the desktop and as the live preview inside Settings.
"""
from __future__ import annotations

import math
import platform

from PySide6.QtCore import (Qt, Signal, QPoint, QPointF, QRectF, QSize, QSettings, QTimer,
                            QEasingCurve, QPropertyAnimation)
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QCursor, QGuiApplication
from PySide6.QtWidgets import (QWidget, QApplication, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QToolButton, QSizePolicy)

from i18n import tr, amp

SHAPES = ('wheel', 'square', 'rectangle', 'bar')
POSITIONS = ('cursor', 'center', 'top', 'bottom', 'left', 'right', 'remember')
SHAPE_LABELS = {'wheel': 'Wheel', 'square': 'Square', 'rectangle': 'Rectangle', 'bar': 'Bar'}
POSITION_LABELS = {
    'cursor': 'Next to the mouse pointer', 'center': 'Center of the screen',
    'top': 'Top of the screen', 'bottom': 'Bottom of the screen',
    'left': 'Left edge', 'right': 'Right edge', 'remember': 'Where I last dragged it',
}
MAX_ACTIONS = {'wheel': 6, 'square': 9, 'rectangle': 8, 'bar': 8}


def action_icon(kind, color, size=30):
    """Vector pictogram from the wheel renderer, as a crisp icon."""
    from quickwheel import _draw_action_icon
    ratio = 2
    pix = QPixmap(size * ratio, size * ratio)
    pix.setDevicePixelRatio(ratio)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    scale = size / 32.0
    p.scale(scale, scale)
    _draw_action_icon(p, 16, 16, kind, QColor(color))
    p.end()
    return QIcon(pix)


def place_rect(mode, w, h, cursor, avail, remembered=None, margin=14):
    """Top-left for a hub of w×h using a position mode; always on-screen."""
    if mode == 'remember' and remembered is not None:
        cx, cy = remembered
    elif mode == 'center':
        cx, cy = avail.center().x(), avail.center().y()
    elif mode == 'top':
        cx, cy = avail.center().x(), avail.top() + margin + h / 2
    elif mode == 'bottom':
        cx, cy = avail.center().x(), avail.bottom() - margin - h / 2
    elif mode == 'left':
        cx, cy = avail.left() + margin + w / 2, avail.center().y()
    elif mode == 'right':
        cx, cy = avail.right() - margin - w / 2, avail.center().y()
    else:
        cx, cy = cursor.x(), cursor.y()
    x = int(cx - w / 2)
    y = int(cy - h / 2)
    x = max(avail.left(), min(x, avail.left() + max(0, avail.width() - w)))
    y = max(avail.top(), min(y, avail.top() + max(0, avail.height() - h)))
    return x, y


def HubTile(key, compact, accent, parent=None):
    """An Action Hub tile: pictogram above a label that wraps instead of being cut."""
    from quickwheel import WHEEL_LABELS
    label, kind = WHEEL_LABELS.get(key, (key, 'more'))
    tile = WrapButton(tr(label), action_icon(kind, QColor(accent).lighter(150).name(), 30),
                      vertical=True, icon_px=24 if compact else 28, parent=parent)
    tile.key = key
    tile.setCursor(Qt.PointingHandCursor)
    tile.setObjectName('hubTile')
    tile.setFocusPolicy(Qt.StrongFocus)
    if key == 'rar_files':
        from core_ops import rar_writer_available
        tile.setEnabled(rar_writer_available())
    return tile


class PanelContent(QWidget):
    """Header (logo · file summary · tools) + tiles. Paints its own glass card."""
    action_requested = Signal(object)

    def __init__(self, preview=False, parent=None):
        super().__init__(parent)
        self.preview = preview
        self.shape = 'square'
        self.vertical = False
        self.scale = 1.0
        self.opacity_setting = 78
        self.accent = '#3896FF'
        self.glow = 58
        self.actions = []
        self.paths = []
        self.persistent = False
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._outer = QVBoxLayout(self)
        self._build()

    # -------------------------------------------------------------- building
    def configure(self, shape, vertical=False, scale=1.0, opacity=78, accent='#3896FF', glow=58):
        self.shape, self.vertical = shape, bool(vertical)
        self.scale = max(0.75, min(1.5, float(scale)))
        self.opacity_setting, self.glow = int(opacity), int(glow)
        self.accent = QColor(accent).name() if QColor(accent).isValid() else '#3896FF'
        self._build()

    def set_context(self, paths, actions, persistent=False):
        self.paths = list(paths)
        self.actions = list(actions)
        self.persistent = persistent
        self._build()

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            elif item.layout():
                self._clear(item.layout())

    def _build(self):
        self._clear(self._outer)
        bar = self.shape == 'bar'
        compact = bar
        pad = round((10 if bar else 14) * self.scale)
        self._outer.setContentsMargins(pad, pad, pad, pad)
        self._outer.setSpacing(round(8 * self.scale))
        tile_w = round((84 if bar else 104) * self.scale)
        tile_h = round((74 if bar else 92) * self.scale)

        # Header: logo, summary, tools. Bars put the tools at the end.
        header = QBoxLayoutFor(self.vertical and bar)
        logo = QLabel()
        from app_assets import logo_png
        logo.setPixmap(QPixmap(logo_png()).scaled(round(22 * self.scale), round(22 * self.scale),
                                                  Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setObjectName('hubLogo')
        logo.setToolTip(tr('Drag to move'))
        header.addWidget(logo, 0, Qt.AlignCenter)
        from file_intelligence import file_summary
        summary_text = ('  ·  '.join(file_summary(self.paths, max_lines=2)) if self.paths
                        else tr('Select files in Finder'))
        if not (bar and self.vertical):
            title = QLabel(summary_text)
            title.setObjectName('hubTitle')
            title.setToolTip(tr('Drag to move'))
            header.addWidget(title, 1)
        self.tool_buttons = []
        for glyph, tip, action in (('+', 'Add more files…', 'add_more'),
                                   ('⋯', 'More tools', 'more_actions'),
                                   ('×', 'Hide', 'hide_hub')):
            btn = QToolButton()
            btn.setText(glyph)
            btn.setToolTip(tr(tip))
            btn.setObjectName('hubTool')
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, a=action: self.action_requested.emit(a))
            header.addWidget(btn, 0, Qt.AlignCenter)
            self.tool_buttons.append(btn)

        grid = QGridLayout()
        grid.setSpacing(round(7 * self.scale))
        self.tiles = []
        if not self.actions:
            empty = QLabel(tr('Select one or more files in Finder, then hover here or press your shortcut.')
                           if not self.preview else '')
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName('hubEmpty')
            empty.setMinimumWidth(round(200 * self.scale))
            grid.addWidget(empty, 0, 0)
        else:
            n = len(self.actions)
            if bar:
                cols = 1 if self.vertical else n
            elif self.shape == 'rectangle':
                cols = 4 if n > 3 else n
            else:
                cols = 3 if n > 4 else (2 if n > 1 else 1)
            for i, key in enumerate(self.actions):
                tile = HubTile(key, compact, self.accent)
                tile.setFixedSize(tile_w, tile_h)
                tile.clicked.connect(lambda _=False, k=key: self.action_requested.emit(k))
                grid.addWidget(tile, i // cols, i % cols)
                self.tiles.append(tile)

        if bar and not self.vertical:
            row = QHBoxLayout()
            row.setSpacing(round(10 * self.scale))
            row.addLayout(header)
            row.addLayout(grid)
            self._outer.addLayout(row)
        else:
            self._outer.addLayout(header)
            self._outer.addLayout(grid)
        self._apply_style(tile_w)
        self.adjustSize()

    def _apply_style(self, tile_w):
        accent = QColor(self.accent)
        hover = QColor(accent); hover.setAlpha(150)
        fs = max(9, round((10 if self.shape == 'bar' else 11) * self.scale))
        self.setStyleSheet(f'''
            QLabel#hubTitle {{ color:#E6F2FF; font-size:{max(11, round(12*self.scale))}px; font-weight:700; background:transparent; }}
            QLabel#hubEmpty {{ color:#A9C5E4; font-size:{max(11, round(12*self.scale))}px; background:transparent; padding:10px; }}
            QLabel#hubLogo {{ background:transparent; }}
            QToolButton#hubTool {{ color:#CFE5FF; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.10);
                                   border-radius:{round(9*self.scale)}px; min-width:{round(22*self.scale)}px;
                                   min-height:{round(22*self.scale)}px; font-size:{round(14*self.scale)}px; font-weight:700; }}
            QToolButton#hubTool:hover {{ background:{hover.name(QColor.HexArgb)}; color:white; }}
            QToolButton#hubTile {{ color:#EAF4FF; background:rgba(255,255,255,0.05);
                                   border:1px solid rgba(255,255,255,0.09); border-radius:{round(12*self.scale)}px;
                                   font-size:{fs}px; font-weight:600; padding:{round(5*self.scale)}px 2px; }}
            QToolButton#hubTile:hover {{ background:{hover.name(QColor.HexArgb)}; border-color:{accent.name()}; color:white; }}
            QToolButton#hubTile:pressed {{ background:{accent.name()}; }}
            QToolButton#hubTile:disabled {{ color:#6F86A3; }}
            QToolButton#hubTile:focus {{ border-color:{accent.lighter(130).name()}; }}
            QLabel#wrapText {{ color:#EAF4FF; font-size:{fs}px; font-weight:600; }}
        ''')

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        radius = 16 * self.scale if self.shape != 'bar' else 18 * self.scale
        accent = QColor(self.accent)
        strength = max(0, min(100, self.glow)) / 100
        for i, a in enumerate((18, 10)):
            halo = QColor(accent)
            halo.setAlpha(int(a * strength))
            p.setPen(QPen(halo, 3 + i * 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), radius, radius)
        bg = QColor(8, 24, 48)
        bg.setAlpha(max(25, min(95, self.opacity_setting)) * 255 // 100 + 10)
        p.setBrush(bg)
        border = QColor(accent)
        border.setAlpha(int(110 + 110 * strength))
        p.setPen(QPen(border, 1.3))
        p.drawRoundedRect(r, radius, radius)
        p.end()


def QBoxLayoutFor(vertical):
    lay = QVBoxLayout() if vertical else QHBoxLayout()
    lay.setSpacing(6)
    return lay


_NO_COMPOSITOR = None


def needs_shape_mask():
    """Linux X11 without a compositor draws transparent windows black.

    Then the hub gets a window mask instead (crisp edges, no black corners).
    With a compositor (GNOME, KDE, …) real transparency keeps the soft glow."""
    global _NO_COMPOSITOR
    if _NO_COMPOSITOR is None:
        _NO_COMPOSITOR = False
        try:
            import sys
            from PySide6.QtGui import QGuiApplication
            if sys.platform.startswith('linux') and QGuiApplication.platformName() == 'xcb':
                from Xlib import display as xdisplay
                d = xdisplay.Display()
                owner = d.get_selection_owner(d.intern_atom(f'_NET_WM_CM_S{d.get_default_screen()}'))
                _NO_COMPOSITOR = not owner or getattr(owner, 'id', owner) == 0
                d.close()
        except Exception:
            _NO_COMPOSITOR = False
    return _NO_COMPOSITOR


def apply_shape_mask(widget, kind='rounded', radius=16, inset=0):
    if not needs_shape_mask():
        return
    from PySide6.QtGui import QRegion, QPainterPath
    r = widget.rect().adjusted(inset, inset, -inset, -inset)
    if kind == 'ellipse':
        widget.setMask(QRegion(r, QRegion.Ellipse))
    else:
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        widget.setMask(QRegion(path.toFillPolygon().toPolygon()))


class PanelWindow(QWidget):
    """Top-level window around PanelContent with the same API as WheelWindow."""
    action_requested = Signal(object)
    hovered = Signal(bool)

    def __init__(self, shape='square'):
        mac = platform.system() == 'Darwin'
        flags = (Qt.Window if mac else Qt.Tool) | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setWindowTitle('Morphix Action Hub')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if mac:
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setAcceptDrops(True)
        self.shape = shape
        self.MAX_ACTIONS = MAX_ACTIONS.get(shape, 8)
        self.position = 'cursor'
        self.persistent = False
        self.actions, self.paths, self.profile = [], [], 'mixed'
        self.content = PanelContent(parent=self)
        self.content.action_requested.connect(self._content_action)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.content)
        self._drag = None
        self._appearance = {}
        self.show_anim = QPropertyAnimation(self, b'windowOpacity')
        self.show_anim.setDuration(115)
        self.show_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.content.installEventFilter(self)

    # same API as WheelWindow ------------------------------------------------
    def set_appearance(self, size=290, opacity=78, accent='#3896FF', glow=58, animation=115,
                       position='cursor', persistent=False, **_):
        self.position = position if position in POSITIONS else 'cursor'
        self.persistent = bool(persistent)
        self.show_anim.setDuration(max(0, min(400, int(animation))))
        self._appearance = dict(scale=int(size) / 290.0, opacity=opacity, accent=accent, glow=glow)
        self._configure()

    def _configure(self):
        vertical = self.shape == 'bar' and self.position in ('left', 'right')
        self.content.configure(self.shape, vertical=vertical, **self._appearance)
        self.content.set_context(self.paths, self.actions, self.persistent)
        self._fit()

    def _fit(self):
        lay = self.content.layout()
        lay.activate()
        need = lay.sizeHint().expandedTo(lay.minimumSize())
        self.content.setMinimumSize(lay.minimumSize())
        self.content.resize(need)
        self.setMinimumSize(need)
        self.resize(need)
        apply_shape_mask(self, 'rounded', round(16 * getattr(self.content, 'scale', 1)))

    def set_context(self, paths, profile, actions):
        self.paths, self.profile = list(paths), profile
        self.actions = list(actions)[:self.MAX_ACTIONS]
        self.content.set_context(self.paths, self.actions, self.persistent)
        was_visible = self.isVisible()
        old_center = self.geometry().center()
        self._fit()
        if was_visible and self.position in ('cursor', 'remember'):
            # Keep the panel where the user sees it while files change.
            self.move(old_center - QPoint(self.width() // 2, self.height() // 2))
        elif was_visible:
            self._place()

    def invoke_action(self, action):
        if action not in self.actions:
            return
        print(f'[Morphix] Hub action clicked: {action}', flush=True)
        if not self.persistent:
            self.show_anim.stop()
            self.hide()
        QTimer.singleShot(0, lambda a=action: self.action_requested.emit(a))

    def _content_action(self, action):
        if action in ('add_more', 'more_actions', 'hide_hub'):
            QTimer.singleShot(0, lambda a=action: self.action_requested.emit(
                'center_menu' if a == 'add_more' else a))
            return
        self.invoke_action(action)

    def _place(self):
        pointer = QCursor.pos()
        prefs = QSettings('Morphix', 'Morphix')
        remembered = None
        if prefs.contains('hub_last_x') and prefs.contains('hub_last_y'):
            remembered = (int(prefs.value('hub_last_x')), int(prefs.value('hub_last_y')))
        anchor = QPoint(*remembered) if (self.position == 'remember' and remembered) else pointer
        screen = QGuiApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is None:
            return
        x, y = place_rect(self.position, self.width(), self.height(), pointer,
                          screen.availableGeometry(), remembered)
        self.move(x, y)

    def display(self):
        self._fit()
        self._place()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        _mac_activate_and_float(self, self.persistent)
        self.show_anim.stop()
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(1.0)
        self.show_anim.start()
        print(f'[Morphix] Hub visible ({self.shape}): {len(self.actions)} actions, '
              f'{len(self.paths)} file(s)', flush=True)

    # dragging / hover / keys -----------------------------------------------
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        t = event.type()
        if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.pos()
            self._drag_start = event.globalPosition().toPoint()
        elif t == QEvent.MouseMove and self._drag is not None:
            self.move(event.globalPosition().toPoint() - self._drag)
        elif t == QEvent.MouseButtonRelease and self._drag is not None:
            moved = (event.globalPosition().toPoint() - self._drag_start).manhattanLength() > 6
            self._drag = None
            if moved:
                prefs = QSettings('Morphix', 'Morphix')
                c = self.geometry().center()
                prefs.setValue('hub_last_x', c.x())
                prefs.setValue('hub_last_y', c.y())
        elif t == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self.action_requested.emit('center_menu')
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self.hovered.emit(True)
        if self.persistent:
            _mac_activate_and_float(self, True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit(False)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.persistent:
            self.hide()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        self.action_requested.emit(('add_paths', paths))
        event.acceptProposedAction()


def _mac_activate_and_float(widget, all_spaces):
    """macOS: make the panel clickable at once; optionally show on every Space."""
    if platform.system() != 'Darwin':
        return
    try:
        from AppKit import NSApplication
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        import objc
        view = objc.objc_object(c_void_p=int(widget.winId()))
        window = view.window()
        if window is not None:
            window.setHidesOnDeactivate_(False)
            if all_spaces:
                # canJoinAllSpaces | stationary | fullScreenAuxiliary
                window.setCollectionBehavior_((1 << 0) | (1 << 4) | (1 << 8))
        widget.raise_()
        widget.activateWindow()
    except Exception as exc:
        print(f'[Morphix] Hub activation: {exc}', flush=True)


class WrapButton(QToolButton):
    """Button whose label wraps onto two lines instead of being cut off.

    Used by Action Hub tiles (icon above text) and Studio tool rows
    (icon beside text). Child labels ignore the mouse so clicks reach the button.
    """
    def __init__(self, text, icon, vertical=True, icon_px=28, parent=None):
        super().__init__(parent)
        self.setText('')
        lay = QVBoxLayout(self) if vertical else QHBoxLayout(self)
        lay.setContentsMargins(6, 7, 6, 6) if vertical else lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(4 if vertical else 10)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(icon_px, icon_px))
        self.icon_label.setObjectName('wrapIcon')
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setObjectName('wrapText')
        for lbl in (self.icon_label, self.text_label):
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl.setStyleSheet('background: transparent; border: 0;')
        if vertical:
            self.icon_label.setAlignment(Qt.AlignCenter)
            self.text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            lay.addWidget(self.icon_label)
            lay.addWidget(self.text_label, 1)
        else:
            self.icon_label.setFixedWidth(icon_px + 2)
            self.text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeading)
            lay.addWidget(self.icon_label)
            lay.addWidget(self.text_label, 1)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setToolTip(text)

    def sizeHint(self):
        return self.layout().sizeHint()

    def minimumSizeHint(self):
        return self.layout().minimumSize()

    def hasHeightForWidth(self):
        return self.layout().hasHeightForWidth()

    def heightForWidth(self, width):
        return self.layout().totalHeightForWidth(width)
