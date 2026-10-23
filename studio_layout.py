"""Morphix Studio visual workbench, separate from the always-on Action Hub."""
from __future__ import annotations

import platform

from PySide6.QtCore import Qt, QSettings, QSize, QRect
from PySide6.QtGui import QFont, QFontMetrics, QPixmap
from PySide6.QtWidgets import (QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
    QPushButton, QSplitter, QScrollArea, QProgressBar, QTextEdit)

from i18n import tr, start_side, is_rtl, amp
from shortcut_logic import display_shortcut


def _label(text, ident=None, wordwrap=False):
    item = QLabel(text)
    if ident:
        item.setObjectName(ident)
    item.setWordWrap(wordwrap)
    return item


def _reserve_wrapped_height(label, width):
    """Fix the height of a word-wrapped label to what its text really needs."""
    label.ensurePolished()
    font = QFont(label.font())
    size = {'onlineBadge': 10, 'caption': 12}.get(label.objectName())
    if size:
        font.setPixelSize(size)
    if label.objectName() == 'onlineBadge':
        font.setWeight(QFont.ExtraBold)
    rect = QFontMetrics(font).boundingRect(QRect(0, 0, width, 2000), Qt.TextWordWrap, label.text())
    label.setFixedWidth(width)
    label.setFixedHeight(rect.height() + 6)


def action_button(key, text):
    """A tool button with the same pictogram the Action Hub uses."""
    from quickwheel import WHEEL_LABELS
    from hub_panel import action_icon, WrapButton
    kind = WHEEL_LABELS.get(key, ('', 'more'))[1]
    btn = WrapButton(text, action_icon(kind, '#8CC8FF', 26), vertical=False, icon_px=22)
    btn.setObjectName('actionButton')
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def build_studio_ui(w):
    root = QWidget()
    root.setObjectName('studioRoot')
    w.setCentralWidget(root)
    columns = QHBoxLayout(root)
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(0)

    # ------------------------------------------------------------ sidebar
    sidebar = QFrame()
    sidebar.setObjectName('studioSidebar')
    sidebar.setFixedWidth(238)
    nav = QVBoxLayout(sidebar)
    nav.setContentsMargins(18, 24, 16, 18)
    nav.setSpacing(6)

    brand = QHBoxLayout()
    brand.setSpacing(10)
    logo = QLabel()
    from app_assets import logo_png
    logo.setPixmap(QPixmap(logo_png()).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    logo.setFixedSize(40, 40)
    brand.addWidget(logo)
    brand.addWidget(_label('Morphix', 'studioBrand'), 1)
    nav.addLayout(brand)
    nav.addSpacing(4)
    nav.addWidget(_label(tr('YOUR FILE TOOLKIT'), 'studioOverline'))
    byline = _label(tr('By Yousef'), 'byline')
    italic = QFont(byline.font())
    italic.setItalic(True)
    byline.setFont(italic)
    nav.addWidget(byline)
    nav.addSpacing(22)

    def add_nav(text, cb, selected=False):
        from ui_kit import NavButton
        glyph, _, label = text.partition('   ')
        btn = NavButton(label, glyph, checkable=True)
        btn.setChecked(selected)
        if not selected:
            btn.setCheckable(False)
        if cb:
            btn.clicked.connect(cb)
        nav.addWidget(btn)
        return btn

    nav.addWidget(_label(tr('WORKSPACE'), 'navHeader'))
    add_nav('▦   ' + tr('Files & tools'), None, True)
    add_nav('◎   ' + tr('Show the Action Hub'), w.open_quick_wheel)
    nav.addSpacing(14)
    nav.addWidget(_label(tr('SETTINGS'), 'navHeader'))
    add_nav('◐   ' + tr('Action Hub appearance'), w.open_wheel_settings)
    add_nav('⌨   ' + tr('Keyboard shortcut'), w.open_shortcuts)
    add_nav('⬇   ' + tr('Add-ons'), w.open_addons)
    add_nav('Aa   ' + tr('Language'), w.open_language)
    from branding import AboutDialog
    add_nav('ⓘ   ' + tr('About & contact'), lambda: AboutDialog(w).exec())
    nav.addStretch()
    status = QFrame()
    status.setObjectName('backgroundCard')
    status_layout = QVBoxLayout(status)
    status_layout.setContentsMargins(13, 11, 13, 11)
    status_layout.setSpacing(3)
    # Wrapped labels in a fixed-width sidebar get a wrong height from Qt
    # (the lines overlap and get clipped), so reserve the real wrapped height.
    inner_w = 238 - 18 - 16 - 13 - 13 - 4
    for text, name in (('●  ' + tr('RUNNING IN THE BACKGROUND'), 'onlineBadge'),
                       (tr('Closing Studio keeps the Action Hub and shortcut working.'), 'caption')):
        lbl = _label(text, name, True)
        _reserve_wrapped_height(lbl, inner_w)
        status_layout.addWidget(lbl)
    status.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    nav.addWidget(status)
    add_nav('↙   ' + tr('Close Studio'), w.close)
    columns.addWidget(sidebar)

    # ------------------------------------------------------------ body
    body = QWidget()
    body.setObjectName('studioBody')
    content = QVBoxLayout(body)
    content.setContentsMargins(30, 26, 30, 20)
    content.setSpacing(16)
    columns.addWidget(body, 1)

    title_row = QHBoxLayout()
    heading = QVBoxLayout()
    heading.setSpacing(3)
    heading.addWidget(_label(tr('Your files'), 'studioTitle'))
    heading.addWidget(_label(tr('Add files, pick a tool, and Morphix does the rest — all on this computer.'), 'caption', True))
    title_row.addLayout(heading, 1)
    title_row.addWidget(_label('●  ' + tr('PRIVATE & OFFLINE'), 'privacyBadge'), 0, Qt.AlignTop)
    content.addLayout(title_row)

    hero = QFrame()
    hero.setObjectName('heroCard')
    hero_row = QHBoxLayout(hero)
    hero_row.setContentsMargins(20, 14, 16, 14)
    message = QVBoxLayout()
    message.setSpacing(4)
    message.addWidget(_label(tr('Your files, one shortcut away.'), 'heroTitle'))
    w.hero_shortcut = _label(_shortcut_display(), 'heroCaption')
    message.addWidget(w.hero_shortcut)
    hero_row.addLayout(message, 1)
    customize = QPushButton(tr('Customize the Action Hub'))
    customize.setObjectName('primaryButton')
    customize.setCursor(Qt.PointingHandCursor)
    customize.clicked.connect(w.open_wheel_settings)
    hero_row.addWidget(customize)
    content.addWidget(hero)

    tools = QHBoxLayout()
    tools.setSpacing(8)
    for text, callback, primary in [
            ('＋  ' + tr('Add files'), w.add_files, True),
            (tr('Remove selected'), w.remove_selected, False),
            (tr('Clear list'), w.clear_files, False),
            (tr('All tools…'), w.show_actions, False)]:
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        if primary:
            b.setObjectName('primaryButton')
        b.clicked.connect(callback)
        tools.addWidget(b)
    tools.addStretch()
    content.addLayout(tools)

    split = QSplitter(Qt.Horizontal)
    split.setChildrenCollapsible(False)
    split.setHandleWidth(14)
    content.addWidget(split, 1)

    file_card = QFrame()
    file_card.setObjectName('card')
    fl = QVBoxLayout(file_card)
    fl.setContentsMargins(15, 16, 15, 14)
    fl.setSpacing(8)
    header = QHBoxLayout()
    header.addWidget(_label(tr('Files'), 'cardTitle'))
    header.addStretch()
    w.count = _label(tr('{n} files', n=0), 'fileCount')
    header.addWidget(w.count)
    fl.addLayout(header)
    from main import DropList
    w.files = DropList()
    w.files.setToolTip(tr('Drop files here, or use Add files'))
    w.files.paths_dropped.connect(w.append_files)
    w.files.setContextMenuPolicy(Qt.CustomContextMenu)
    w.files.customContextMenuRequested.connect(lambda _: w.show_actions())
    fl.addWidget(w.files, 1)
    w.empty_hint = _label('⤓\n' + tr('Drag files here from any folder'), 'emptyHint', True)
    w.empty_hint.setAlignment(Qt.AlignCenter)
    w.empty_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    w.empty_hint.setParent(w.files.viewport())
    w.files.viewport().installEventFilter(_Centerer(w.empty_hint, w.files.viewport()))
    split.addWidget(file_card)

    act_card = QFrame()
    act_card.setObjectName('card')
    ac = QVBoxLayout(act_card)
    ac.setContentsMargins(15, 16, 15, 14)
    ac.setSpacing(8)
    ac.addWidget(_label(tr('Tools for these files'), 'cardTitle'))
    w.hint = _label(tr('Add files to see the tools that fit them.'), 'caption', True)
    ac.addWidget(w.hint)
    scroll = QScrollArea()
    scroll.setObjectName('actionsScroll')
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    inner = QWidget()
    inner.setObjectName('actionsInner')
    w.action_box = QVBoxLayout(inner)
    from PySide6.QtWidgets import QLayout
    w.action_box.setSizeConstraint(QLayout.SetMinimumSize)   # scroll instead of squashing
    w.action_box.setContentsMargins(0, 2, 0, 2)
    w.action_box.setSpacing(7)
    scroll.setWidget(inner)
    ac.addWidget(scroll, 1)
    split.addWidget(act_card)
    split.setSizes([470, 420])

    activity = QFrame()
    activity.setObjectName('activityCard')
    activity_layout = QVBoxLayout(activity)
    activity_layout.setContentsMargins(15, 10, 15, 10)
    activity_layout.setSpacing(7)
    activity_layout.addWidget(_label(tr('ACTIVITY  ·  Everything stays on your computer'), 'studioOverline'))
    w.progress = QProgressBar()
    w.progress.setValue(0)
    w.progress.setFixedHeight(8)
    w.progress.setTextVisible(False)
    progress_row = QHBoxLayout()
    progress_row.addWidget(w.progress, 1)
    w.cancel_button = QPushButton(tr('Cancel'))
    w.cancel_button.setCursor(Qt.PointingHandCursor)
    w.cancel_button.setVisible(False)
    w.cancel_button.clicked.connect(w.cancel_action)
    progress_row.addWidget(w.cancel_button)
    w.reveal_button = QPushButton(tr('Show in Finder') if platform.system() == 'Darwin' else tr('Show in folder'))
    w.reveal_button.setCursor(Qt.PointingHandCursor)
    w.reveal_button.setVisible(False)
    w.reveal_button.clicked.connect(w.reveal_outputs)
    progress_row.addWidget(w.reveal_button)
    activity_layout.addLayout(progress_row)
    w.status = QTextEdit()
    w.status.setReadOnly(True)
    w.status.setMaximumHeight(56)
    w.status.setPlainText(tr('Ready. Drop files to get started.'))
    activity_layout.addWidget(w.status)
    content.addWidget(activity)
    w.files.itemSelectionChanged.connect(w.refresh_actions)
    w.setStyleSheet(STYLE.replace('{start}', start_side())
                    .replace('{spacing}', '0px' if is_rtl() else '1px')
                    .replace('{overline}', '12' if is_rtl() else '10'))
    w.refresh_actions()


class _Centerer(QWidget):
    """Keeps the empty-state hint centered in the file list."""
    def __init__(self, label, viewport):
        super().__init__(viewport)
        self.label = label
        self.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.label.setGeometry(0, 0, obj.width(), obj.height())
        return False


def _shortcut_display():
    mac = platform.system() == 'Darwin'
    default = '<cmd>+<shift>+m' if mac else '<ctrl>+<shift>+m'
    shortcut = str(QSettings('Morphix', 'Morphix').value('shortcut', default))
    return tr('Select files anywhere, then press') + '  ' + display_shortcut(shortcut, mac)


STYLE = """
QMainWindow, QWidget#studioRoot { background:#081322; color:#EDF5FF; }
QWidget#studioBody { background:#0A1526; }
QFrame#studioSidebar { background:#0D1B30; border:0; }
QFrame#card, QFrame#activityCard { background:#101E33; border:1px solid #223A57; border-radius:16px; }
QFrame#heroCard { background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #17396A, stop:1 #112A4D);
                  border:1px solid #3570B3; border-radius:16px; }
QFrame#backgroundCard { background:#10283F; border:1px solid #23496B; border-radius:12px; }
QLabel { background:transparent; color:#E8F1FD; }
QLabel#studioBrand { color:#A6D4FF; font-size:26px; font-weight:800; }
QLabel#studioOverline, QLabel#navHeader { color:#7F9BBE; font-size:{overline}px; font-weight:700; letter-spacing:{spacing}; }
QLabel#navHeader { padding:4px 4px 2px 4px; }
QLabel#byline { color:#9CC6F2; font-size:13px; }
QLabel#studioTitle { color:#FFFFFF; font-size:28px; font-weight:800; }
QLabel#caption, QLabel#heroCaption { color:#97B2D0; font-size:12px; }
QLabel#heroCaption { color:#BBD9FD; }
QLabel#heroTitle { color:#F6FAFF; font-size:17px; font-weight:700; }
QLabel#onlineBadge { color:#8FF0D7; font-size:10px; font-weight:800; }
QLabel#cardTitle { color:#F3F8FF; font-size:16px; font-weight:700; }
QLabel#emptyHint { color:#5F7EA3; font-size:15px; }
QLabel#privacyBadge { background:#0F3540; border:1px solid #24606F; color:#92EAD2; padding:7px 11px;
                      border-radius:12px; font-size:10px; font-weight:700; }
QLabel#fileCount { background:#1C3858; border-radius:10px; color:#B6D8FC; padding:4px 10px; }
QPushButton { color:#D8E8FC; background:#18304D; border:1px solid #2B4D73; border-radius:10px;
              padding:10px 14px; font-size:12px; font-weight:600; }
QPushButton:hover { background:#22476C; border-color:#6FB0FA; }
QPushButton:disabled { color:#5D7493; border-color:#1F3753; }
QPushButton#primaryButton { background:#247FE4; color:#FFFFFF; border:1px solid #4F9FF9; font-weight:700; }
QPushButton#primaryButton:hover { background:#3A95F5; }
QToolButton#navButton { background:transparent; border:0; border-radius:10px; }
QToolButton#navButton:hover { background:#18324F; }
QToolButton#navButton:checked { background:#1D4C82; border:1px solid #3170B4; }
QToolButton#navButton QLabel { background:transparent; color:#AFC2DE; font-size:13px; font-weight:600; }
QToolButton#navButton:checked QLabel, QToolButton#navButton:hover QLabel { color:#FFFFFF; }
QToolButton#actionButton { background:#142944; border:1px solid #23446A; border-radius:10px; }
QToolButton#actionButton:hover { background:#1F4A7A; border-color:#5FA8FA; }
QToolButton#actionButton:disabled { background:#0F1F33; }
QToolButton#actionButton QLabel#wrapText { color:#E3EFFD; font-size:13px; font-weight:600; }
QListWidget { background:#0B1729; border:1px dashed #33557A; border-radius:12px; padding:6px; outline:none;
              color:#E3EEFB; font-size:13px; }
QListWidget::item { padding:9px; border-radius:8px; }
QListWidget::item:selected { background:#2675C6; color:#FFFFFF; }
QScrollArea#actionsScroll, QWidget#actionsInner { background:transparent; border:0; }
QProgressBar { background:#22344B; border:0; border-radius:4px; }
QProgressBar::chunk { background:#459EFC; border-radius:4px; }
QTextEdit { background:transparent; border:0; color:#B4CDE8; font-size:12px; }
QSplitter::handle { background:transparent; }
QMenu { background:#13283F; border:1px solid #2E5276; color:#E7F1FD; padding:4px; }
QMenu::item { padding:8px 22px; border-radius:6px; }
QMenu::item:selected { background:#24609D; }
QScrollBar:vertical { background:transparent; width:9px; }
QScrollBar::handle:vertical { background:#2A4A6E; border-radius:4px; min-height:30px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; }
"""
