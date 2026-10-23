"""Morphix Settings: Action Hub look & behaviour, file actions, shortcut, startup,
language and about. Changes preview live and apply when "Save" is pressed.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QPainter, QDesktopServices, QIcon, QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QComboBox, QFrame, QSlider, QCheckBox, QListWidget, QListWidgetItem, QButtonGroup,
    QStackedWidget, QScrollArea, QMessageBox, QColorDialog, QRadioButton,
)

import i18n
from i18n import tr, start_side, amp
from shortcut_recorder import ShortcutRecorder
from quickwheel import (ACCENT_COLORS, DEFAULT_SHORTCUT, PROFILES, WHEEL_LABELS,
                        _render_wheel, validate_shortcut, migrate_hub_settings)
from hub_panel import (SHAPES, SHAPE_LABELS, POSITIONS, POSITION_LABELS, MAX_ACTIONS,
                       PanelContent, action_icon)


class WheelPreview(QWidget):
    """The wheel exactly as drawn on the desktop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 240)
        self.actions = list(PROFILES['pdf_multi'][1])
        self.files = ['Report.pdf', 'Notes.pdf', 'Slides.pdf']
        self.opacity, self.accent, self.glow, self.diameter = 78, ACCENT_COLORS['Blue'], 58, 290

    def paintEvent(self, event):
        p = QPainter(self)
        size = min(self.width() - 8, self.height() - 8, max(174, round(self.diameter * .78)))
        p.translate((self.width() - size) / 2, (self.height() - size) / 2)
        _render_wheel(p, size, self.actions[:6], self.files, self.opacity, self.accent, self.glow, hover=0)
        p.end()


class HubPreview(QWidget):
    """Live preview of the Action Hub.

    Panels are rendered at their real size into an image and then scaled to fit
    the card, so tiles can never be squeezed or overlap (as happened when the
    live widget was placed inside a card narrower than the panel).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.wheel = WheelPreview(self)
        self.panel = PanelContent(preview=True)            # never shown on screen
        self.panel.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.pixmap = None
        self.shape = 'wheel'
        self._last = None

    def refresh(self, shape, position, size, opacity, accent, glow, actions, files):
        self._last = (shape, position, size, opacity, accent, glow, actions, files)
        self.shape = shape
        if shape == 'wheel':
            w = self.wheel
            w.opacity, w.accent, w.glow, w.diameter = opacity, accent, glow, size
            w.actions, w.files = actions[:6], files
            w.setGeometry(self.rect())
            w.show()
            w.update()
            self.pixmap = None
        else:
            self.wheel.hide()
            vertical = shape == 'bar' and position in ('left', 'right')
            self.panel.configure(shape, vertical=vertical, scale=min(1.2, max(0.8, size / 290.0)),
                                 opacity=opacity, accent=accent, glow=glow)
            shown = actions[:MAX_ACTIONS[shape]]
            if shape == 'bar':
                shown = shown[:4]          # keep the sample readable inside the card
            self.panel.set_context(files, shown)
            self.panel.layout().activate()
            self.panel.adjustSize()
            self.panel.resize(self.panel.layout().sizeHint().expandedTo(self.panel.layout().minimumSize()))
            from PySide6.QtGui import QRegion
            from PySide6.QtCore import QPoint
            dpr = max(1.0, self.devicePixelRatioF())
            pix = QPixmap(self.panel.size() * dpr)
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.transparent)
            self.panel.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
            self.pixmap = pix
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.wheel.setGeometry(self.rect())

    def paintEvent(self, event):
        if self.pixmap is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        dpr = self.pixmap.devicePixelRatio()
        w, h = self.pixmap.width() / dpr, self.pixmap.height() / dpr
        scale = min(1.0, (self.width() - 16) / w, (self.height() - 16) / h)
        tw, th = w * scale, h * scale
        from PySide6.QtCore import QRectF
        p.drawPixmap(QRectF((self.width() - tw) / 2, (self.height() - th) / 2, tw, th),
                     self.pixmap, QRectF(self.pixmap.rect()))
        p.end()


class ShapeCard(QPushButton):
    def __init__(self, shape):
        super().__init__()
        self.shape = shape
        self.setCheckable(True)
        self.setObjectName('shapeCard')
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(96, 78)
        self.setText(tr(SHAPE_LABELS[shape]))
        self.setIcon(QIcon(self._pictogram()))
        self.setIconSize(QPixmap(self._pictogram()).size() / 2)

    def _pictogram(self):
        pix = QPixmap(96, 56)
        pix.setDevicePixelRatio(2)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor('#8CC8FF'))
        p.setBrush(QColor(140, 200, 255, 40))
        if self.shape == 'wheel':
            p.drawEllipse(14, 2, 22, 22)
            p.setBrush(QColor('#0D1B30'))
            p.drawEllipse(21, 9, 8, 8)
        elif self.shape == 'square':
            for i in range(3):
                for j in range(2):
                    p.drawRoundedRect(13 + i * 8, 4 + j * 9, 6, 7, 1.5, 1.5)
        elif self.shape == 'rectangle':
            for i in range(4):
                for j in range(2):
                    p.drawRoundedRect(9 + i * 8, 6 + j * 8, 6, 6, 1.5, 1.5)
        else:
            p.drawRoundedRect(5, 10, 38, 8, 3, 3)
        p.end()
        return pix


class WheelSettings(QDialog):
    PAGES = ('Action Hub', 'File actions', 'Keyboard shortcut', 'Startup & background', 'Add-ons', 'Language', 'About')

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        migrate_hub_settings(settings)
        self.setWindowTitle(tr('Morphix — Settings'))
        self.setMinimumSize(860, 640)
        self.resize(1040, 760)
        self.drafts = {}
        self.current_profile = None
        self.accent = str(settings.value('wheel_accent', ACCENT_COLORS['Blue']))
        if not QColor(self.accent).isValid():
            self.accent = ACCENT_COLORS['Blue']
        self.shape = str(settings.value('hub_shape', 'wheel'))
        if self.shape not in SHAPES:
            self.shape = 'wheel'
        self._build_ui()
        self._load_profile()
        self._refresh_preview()

    # ---------------------------------------------------------------- frame
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)
        root.addLayout(center, 1)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(268)
        s = QVBoxLayout(sidebar)
        s.setContentsMargins(17, 22, 12, 18)
        s.setSpacing(5)
        brand = QHBoxLayout()
        logo = QLabel()
        from app_assets import logo_png
        logo.setPixmap(QPixmap(logo_png()).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.addWidget(logo)
        wordmark = QLabel('Morphix')
        wordmark.setObjectName('wordmark')
        brand.addWidget(wordmark, 1)
        s.addLayout(brand)
        s.addSpacing(16)
        overline = QLabel(tr('SETTINGS'))
        overline.setObjectName('overline')
        s.addWidget(overline)
        s.addSpacing(6)
        self.sidebar_buttons = []
        self.pages = QStackedWidget()
        icons = ['◎', '☷', '⌨', '↗', '⬇', 'Aa', 'ⓘ']
        from ui_kit import NavButton
        for icon, title in zip(icons, self.PAGES):
            b = NavButton(tr(title), icon, checkable=True)
            b.clicked.connect(lambda checked=False, index=len(self.sidebar_buttons): self._switch_page(index))
            s.addWidget(b)
            self.sidebar_buttons.append(b)
        s.addStretch()
        from main import APP_VERSION
        ver = QLabel(f'Morphix {APP_VERSION}')
        ver.setObjectName('description')
        s.addWidget(ver)
        by = QLabel(tr('By Yousef'))
        f = QFont(by.font()); f.setItalic(True); by.setFont(f)
        by.setObjectName('description')
        s.addWidget(by)
        center.addWidget(sidebar)
        center.addWidget(self.pages, 1)

        for builder in (self._build_hub_page, self._build_actions_page, self._build_shortcuts_page,
                        self._build_startup_page, self._build_addons_page, self._build_language_page,
                        self._build_about_page):
            self.pages.addWidget(builder())
        self._switch_page(0)

        footer = QFrame()
        footer.setObjectName('footer')
        bottom = QHBoxLayout(footer)
        bottom.setContentsMargins(24, 12, 24, 12)
        hint = QLabel(tr('The preview updates as you go. Press Save to apply.'))
        hint.setObjectName('description')
        bottom.addWidget(hint)
        bottom.addStretch()
        cancel = QPushButton(tr('Cancel'))
        cancel.setObjectName('secondaryButton')
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr('Save'))
        save.setObjectName('primaryButton')
        save.setDefault(True)
        save.clicked.connect(self.save)
        bottom.addWidget(cancel)
        bottom.addWidget(save)
        root.addWidget(footer)
        self._apply_styles()

    def _switch_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, b in enumerate(self.sidebar_buttons):
            b.setChecked(i == index)

    def _scroll_page(self):
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(28, 26, 28, 22)
        layout.setSpacing(13)
        scroller.setWidget(outer)
        return scroller, layout

    @staticmethod
    def _heading(title, subtitle, layout):
        label = QLabel(title)
        label.setObjectName('pageTitle')
        layout.addWidget(label)
        note = QLabel(subtitle)
        note.setObjectName('description')
        note.setWordWrap(True)
        layout.addWidget(note)

    @staticmethod
    def _text_header(text):
        label = QLabel(text)
        label.setObjectName('sectionHeader')
        return label

    def _add_slider(self, layout, title, min_val, max_val, value, suffix, callback):
        layout.addWidget(self._text_header(title))
        line = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(int(value))
        slider.setPageStep(5)
        slider.setCursor(Qt.PointingHandCursor)
        value_label = QLabel('')
        value_label.setFixedWidth(62)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setObjectName('valueText')
        slider.valueChanged.connect(lambda val: value_label.setText(f'{val}{suffix}'))
        slider.valueChanged.connect(callback)
        value_label.setText(f'{slider.value()}{suffix}')
        line.addWidget(slider, 1)
        line.addWidget(value_label)
        layout.addLayout(line)
        return slider

    # ---------------------------------------------------------------- pages
    def _build_hub_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('Action Hub'),
                      tr('The Action Hub shows the right tools for the files you select. '
                         'Choose its shape, where it appears, and whether it stays on screen.'), layout)

        layout.addWidget(self._text_header(tr('SHAPE')))
        shapes = QHBoxLayout()
        shapes.setSpacing(10)
        self.shape_group = QButtonGroup(self)
        self.shape_cards = {}
        for shape in SHAPES:
            card = ShapeCard(shape)
            card.setChecked(shape == self.shape)
            card.clicked.connect(lambda _=False, sh=shape: self._choose_shape(sh))
            self.shape_group.addButton(card)
            self.shape_cards[shape] = card
            shapes.addWidget(card)
        shapes.addStretch()
        layout.addLayout(shapes)

        h = QHBoxLayout()
        h.setSpacing(18)
        layout.addLayout(h)
        preview_box = QFrame()
        preview_box.setObjectName('previewCard')
        preview_box.setMinimumWidth(320)
        pl = QVBoxLayout(preview_box)
        pl.setContentsMargins(14, 14, 14, 14)
        pl.addWidget(self._text_header(tr('LIVE PREVIEW')))
        self.preview = HubPreview()
        pl.addWidget(self.preview, 1)
        self.preview_caption = QLabel('')
        self.preview_caption.setAlignment(Qt.AlignCenter)
        self.preview_caption.setObjectName('description')
        pl.addWidget(self.preview_caption)
        h.addWidget(preview_box, 3)

        side = QWidget()
        control = QVBoxLayout(side)
        control.setContentsMargins(0, 0, 0, 0)
        control.setSpacing(10)
        control.addWidget(self._text_header(tr('WHERE IT APPEARS')))
        self.position_combo = QComboBox()
        for key in POSITIONS:
            self.position_combo.addItem(tr(POSITION_LABELS[key]), key)
        idx = self.position_combo.findData(str(self.settings.value('hub_position', 'cursor')))
        self.position_combo.setCurrentIndex(max(0, idx))
        self.position_combo.currentIndexChanged.connect(lambda *_: self._refresh_preview())
        control.addWidget(self.position_combo)

        control.addWidget(self._text_header(tr('WHEN IT IS VISIBLE')))
        self.visible_shortcut = QRadioButton()
        self.visible_always = QRadioButton()
        always = str(self.settings.value('hub_visibility', 'shortcut')) == 'always'
        (self.visible_always if always else self.visible_shortcut).setChecked(True)
        control.addWidget(i18n.option_row(self.visible_shortcut, tr('Only when I press the shortcut')))
        control.addWidget(i18n.option_row(self.visible_always,
                          tr('Always on screen (it updates when your mouse moves over it)')))

        self.size_slider = self._add_slider(control, tr('SIZE'), 220, 440,
            self.settings.value('wheel_size', 290), ' px', lambda *_: self._refresh_preview())
        self.opacity_slider = self._add_slider(control, tr('BACKGROUND OPACITY'), 25, 95,
            self.settings.value('wheel_opacity', 78), '%', lambda *_: self._refresh_preview())
        self.glow_slider = self._add_slider(control, tr('EDGE GLOW'), 0, 100,
            self.settings.value('wheel_glow', 58), '%', lambda *_: self._refresh_preview())
        self.animation_slider = self._add_slider(control, tr('OPENING ANIMATION'), 0, 300,
            self.settings.value('wheel_animation', 115), ' ms', lambda *_: self._refresh_preview())
        control.addWidget(self._text_header(tr('ACCENT COLOR')))
        palette = QHBoxLayout()
        palette.setSpacing(9)
        self.swatches = []
        for label, code in ACCENT_COLORS.items():
            swatch = QPushButton('')
            swatch.setFixedSize(28, 28)
            swatch.setToolTip(label)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.clicked.connect(lambda _=False, c=code: self._choose_accent(c))
            self.swatches.append((swatch, code))
            palette.addWidget(swatch)
        custom_color = QPushButton(tr('Custom…'))
        custom_color.setObjectName('secondaryButton')
        custom_color.clicked.connect(self._select_custom_accent)
        palette.addWidget(custom_color)
        palette.addStretch()
        control.addLayout(palette)
        control.addStretch()
        h.addWidget(side, 2)

        actions_button = QPushButton(tr('Choose which tools appear for each file type') + '   ›')
        actions_button.setObjectName('secondaryButton')
        actions_button.clicked.connect(lambda: self._switch_page(1))
        layout.addWidget(actions_button)
        layout.addStretch()
        self._update_swatches()
        return page

    def _build_actions_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('File actions'),
                      tr('For each kind of file, tick the tools you want in the Action Hub and drag them into '
                         'your preferred order. The wheel shows up to 6, the other shapes up to 8 or 9; '
                         'everything else stays under “More tools”.'), layout)
        layout.addWidget(self._text_header(tr('FILE TYPE')))
        self.profile_combo = QComboBox()
        for key, (description, _) in PROFILES.items():
            self.profile_combo.addItem(tr(description), key)
        layout.addWidget(self.profile_combo)
        layout.addWidget(self._text_header(tr('DRAG TO REORDER · TICK TO SHOW')))
        self.action_list = QListWidget()
        self.action_list.setDragDropMode(QListWidget.InternalMove)
        self.action_list.setDefaultDropAction(Qt.MoveAction)
        self.action_list.setMinimumHeight(340)
        self.action_list.setIconSize(QPixmap(22, 22).size())
        from ui_kit import ToolListDelegate
        self.action_list.setItemDelegate(ToolListDelegate(parent=self.action_list))
        self.action_list.setMouseTracking(True)
        self.action_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.action_list.itemChanged.connect(lambda *_: self._actions_changed())
        self.action_list.model().rowsMoved.connect(lambda *_: self._actions_changed())
        layout.addWidget(self.action_list)
        self.action_count = QLabel('')
        self.action_count.setObjectName('description')
        layout.addWidget(self.action_count)
        self.profile_combo.currentIndexChanged.connect(self._load_profile)
        layout.addStretch()
        return page

    def _build_shortcuts_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('Keyboard shortcut'),
                      tr('Click the box, then press the keys you want. It works the same whether your '
                         'keyboard is set to Arabic or English.'), layout)
        card = QFrame()
        card.setObjectName('recorderCard')
        rc = QVBoxLayout(card)
        rc.setContentsMargins(21, 20, 21, 19)
        rc.setSpacing(12)
        rc.addWidget(self._text_header(tr('SHOW THE ACTION HUB')))
        self.shortcut_edit = ShortcutRecorder(str(self.settings.value('shortcut', DEFAULT_SHORTCUT)))
        rc.addWidget(self.shortcut_edit)
        hints = QLabel(tr('Examples: ⌘ Command + Shift + M, Option + M, Ctrl + Delete. Press Esc to cancel.'))
        hints.setObjectName('description')
        hints.setWordWrap(True)
        rc.addWidget(hints)
        controls = QHBoxLayout()
        reset = QPushButton(tr('Restore default'))
        reset.setObjectName('secondaryButton')
        reset.clicked.connect(lambda: self.shortcut_edit.clear_shortcut(DEFAULT_SHORTCUT))
        controls.addWidget(reset)
        controls.addStretch()
        rc.addLayout(controls)
        layout.addWidget(card)
        note = QLabel(tr('Morphix listens to the physical key position, not the letter it types, '
                         'so switching keyboard languages never breaks the shortcut. '
                         'macOS needs Accessibility permission once for shortcuts to work.'))
        note.setObjectName('description')
        note.setWordWrap(True)
        layout.addWidget(note)
        import platform
        if platform.system() == 'Darwin':
            from native_hotkeys import open_accessibility_settings
            allow = QPushButton(tr('Open Accessibility settings'))
            allow.setObjectName('secondaryButton')
            allow.clicked.connect(open_accessibility_settings)
            layout.addWidget(allow, 0, Qt.AlignLeft if not i18n.is_rtl() else Qt.AlignRight)
        layout.addStretch()
        return page

    def _build_startup_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('Startup & background'),
                      tr('Morphix lives quietly in the menu bar. Studio opens only when you ask for it.'), layout)
        panel = QFrame()
        panel.setObjectName('recorderCard')
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 18, 20, 18)
        self.login_checkbox = QCheckBox()
        from autostart import is_enabled
        self.login_checkbox.setChecked(is_enabled())
        pl.addWidget(i18n.option_row(self.login_checkbox, tr('Start Morphix automatically when I log in')))
        sub = QLabel(tr('Only the background helper starts — Studio stays closed until you open it.'))
        sub.setObjectName('description')
        sub.setWordWrap(True)
        pl.addWidget(sub)
        layout.addWidget(panel)
        note = QLabel(tr('Closing Studio does not stop Morphix. To stop it completely, choose '
                         '“Quit Morphix” from the blue M menu.'))
        note.setObjectName('description')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return page

    def _build_addons_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('Add-ons'),
                      tr('Extra tools that are downloaded once. After downloading they work without the internet. '
                         'Everything else in Morphix is already built in.'), layout)
        from addons import addons_widget
        layout.addWidget(addons_widget())
        return page

    def _build_language_page(self):
        page, layout = self._scroll_page()
        self._heading(tr('Language'),
                      tr('Choose the language of the whole app. Morphix restarts to apply it.'), layout)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.lang_group = QButtonGroup(self)
        self.lang_buttons = {}
        for code, label in (('ar', 'العربية'), ('en', 'English')):
            b = QPushButton(label)
            b.setObjectName('langCard')
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(72)
            b.setChecked(i18n.current() == code)
            self.lang_group.addButton(b)
            self.lang_buttons[code] = b
            row.addWidget(b)
        layout.addLayout(row)
        note = QLabel(tr('In Arabic the interface is arranged from right to left.'))
        note.setObjectName('description')
        layout.addWidget(note)
        layout.addStretch()
        return page

    def _build_about_page(self):
        page, layout = self._scroll_page()
        from branding import about_content
        layout.addWidget(about_content())
        layout.addStretch()
        return page

    # ---------------------------------------------------------------- logic
    def _choose_shape(self, shape):
        self.shape = shape
        for sh, card in self.shape_cards.items():
            card.setChecked(sh == shape)
        self._actions_changed()

    def _select_custom_accent(self):
        color = QColorDialog.getColor(QColor(self.accent), self, tr('Choose an accent color'))
        if color.isValid():
            self._choose_accent(color.name())

    def _choose_accent(self, color):
        self.accent = color
        self._update_swatches()
        self._refresh_preview()

    def _update_swatches(self):
        for btn, code in self.swatches:
            active = code.lower() == self.accent.lower()
            btn.setStyleSheet('QPushButton {background:%s; border: %spx solid %s; border-radius:14px; padding:0;}' %
                              (code, 3 if active else 1, '#FFFFFF' if active else '#536A8C'))

    def _collect_current_profile(self):
        if self.current_profile is None:
            return
        self.drafts[self.current_profile] = [
            (self.action_list.item(i).data(Qt.UserRole),
             self.action_list.item(i).checkState() == Qt.Checked)
            for i in range(self.action_list.count())]

    def _load_profile(self, *_):
        self._collect_current_profile()
        profile = self.profile_combo.currentData()
        self.current_profile = profile
        self.action_list.blockSignals(True)
        self.action_list.clear()
        draft = self.drafts.get(profile)
        if draft is None:
            try:
                saved = json.loads(self.settings.value('wheel_v14/' + profile, 'null'))
            except (ValueError, TypeError):
                saved = None
            defaults = PROFILES[profile][1]
            enabled = saved if isinstance(saved, list) else defaults
            from main import supported_actions  # offer every tool that fits this file type
            sample = {'pdf': 'x.pdf', 'image': 'x.png', 'video': 'x.mp4', 'audio': 'x.mp3',
                      'office': 'x.docx'}.get(profile.split('_')[0])
            extra = []
            if sample:
                extra = _actions_for_profile(profile, supported_actions)
            keys = list(dict.fromkeys(enabled + defaults + extra))
            draft = [(k, k in enabled) for k in keys if k in WHEEL_LABELS]
        for key, checked in draft:
            label, glyph = WHEEL_LABELS[key]
            item = QListWidgetItem(action_icon(glyph, '#8CC8FF', 22), tr(label))
            item.setData(Qt.UserRole, key)
            item.setFlags((item.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsUserCheckable)
            item.setData(Qt.CheckStateRole, Qt.Checked if checked else Qt.Unchecked)
            self.action_list.addItem(item)
        self.action_list.blockSignals(False)
        self._actions_changed()

    def _actions_changed(self):
        if self.current_profile is None:
            return
        count = sum(self.action_list.item(i).checkState() == Qt.Checked
                    for i in range(self.action_list.count()))
        self.action_count.setText(tr('{n} selected · {shape} shows up to {max}',
                                     n=count, shape=tr(SHAPE_LABELS[self.shape]), max=MAX_ACTIONS[self.shape]))
        self._refresh_preview()

    def _refresh_preview(self):
        if not hasattr(self, 'preview') or not hasattr(self, 'animation_slider'):
            return
        keys = list(PROFILES['pdf_multi'][1])
        files = ['Report.pdf', 'Notes.pdf', 'Slides.pdf']
        caption = tr(PROFILES['pdf_multi'][0])
        if hasattr(self, 'action_list') and self.current_profile:
            keys = [self.action_list.item(i).data(Qt.UserRole)
                    for i in range(self.action_list.count())
                    if self.action_list.item(i).checkState() == Qt.Checked] or ['more_actions']
            key = self.current_profile
            ext = {'pdf': 'pdf', 'image': 'png', 'video': 'mp4', 'audio': 'mp3', 'office': 'docx'}.get(key.split('_')[0], 'zip')
            files = [f'example.{ext}'] * (1 if key.endswith('single') else 3)
            caption = tr(PROFILES[key][0])
        self.preview.refresh(self.shape, self.position_combo.currentData(), self.size_slider.value(),
                             self.opacity_slider.value(), self.accent, self.glow_slider.value(), keys, files)
        self.preview_caption.setText(caption + ' · ' + tr('Live preview'))

    def save(self):
        if getattr(self.shortcut_edit, '_recording', False):
            QMessageBox.warning(self, tr('Finish recording'),
                                tr('Press a key while holding a modifier, or press Esc to cancel.'))
            self._switch_page(2)
            return
        shortcut = self.shortcut_edit.shortcut()
        if not validate_shortcut(shortcut):
            QMessageBox.warning(self, tr('Invalid shortcut'),
                                tr('Hold a modifier key, then press a letter, Delete or a function key.'))
            self._switch_page(2)
            return
        import platform
        if platform.system() == 'Windows':
            try:
                from windows_hotkeys import parse_shortcut as check_windows_key
                check_windows_key(shortcut)
            except ValueError as error:
                QMessageBox.warning(self, tr('Invalid shortcut'), str(error))
                self._switch_page(2)
                return
        self._collect_current_profile()
        for key, draft in self.drafts.items():
            enabled = [action for action, checked in draft if checked]
            self.settings.setValue('wheel_v14/' + key, json.dumps(
                enabled or (['zip_files'] if key == 'mixed' else ['more_actions'])))
        from autostart import set_enabled
        try:
            set_enabled(self.login_checkbox.isChecked())
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(self, tr('Startup & background'), str(exc))
            self._switch_page(3)
            return
        st = self.settings
        st.setValue('shortcut', shortcut)
        st.setValue('hub_shape', self.shape)
        st.setValue('hub_position', self.position_combo.currentData())
        st.setValue('hub_visibility', 'always' if self.visible_always.isChecked() else 'shortcut')
        st.setValue('wheel_size', self.size_slider.value())
        st.setValue('wheel_opacity', self.opacity_slider.value())
        st.setValue('wheel_glow', self.glow_slider.value())
        st.setValue('wheel_animation', self.animation_slider.value())
        st.setValue('wheel_accent', self.accent)
        new_lang = next(code for code, b in self.lang_buttons.items() if b.isChecked()) \
            if any(b.isChecked() for b in self.lang_buttons.values()) else i18n.current()
        if new_lang != i18n.current():
            answer = QMessageBox.question(
                self, tr('Change language'),
                i18n.trl(new_lang, 'Morphix will restart in the new language. Continue?'))
            if answer != QMessageBox.Yes:
                return
            st.sync()
            i18n.set_language(new_lang)   # saved; the caller restarts Morphix
        st.sync()
        self.accept()

    def _apply_styles(self):
        side = start_side()
        self.setStyleSheet(('''
            QDialog, QWidget { background: #091729; color: #E5EFFC; font-size: 13px; }
            QFrame#sidebar { background: #0B1B31; border: 0; }
            QLabel#wordmark { color: #A6D4FF; font-size: 23px; font-weight: bold; }
            QLabel#overline, QLabel#sectionHeader { color: #8DA6C6; font-size: OVERpx; font-weight: bold; letter-spacing: SPACING; }
            QFrame#sidebar QLabel, QFrame#footer QLabel { background: transparent; }
            QLabel#pageTitle { color: #F1F7FF; font-size: 23px; font-weight: bold; }
            QLabel#description { color: #9EB1CC; font-size: 12px; }
            QLabel#valueText { color: #C5DDFA; font-weight: bold; }
            QFrame#previewCard { background: #0E1C32; border: 1px solid #2B4667; border-radius: 15px; }
            QFrame#previewCard QWidget { background: transparent; }
            QFrame#recorderCard { background:#122842; border:1px solid #355B82; border-radius:15px; }
            QLineEdit#shortcutRecorder { background:#09182F; border:2px solid #417DB7;
                border-radius:12px; color:#FFFFFF; padding:13px; font-weight:bold; font-size:21px; }
            QLineEdit#shortcutRecorder[recording="true"] { border-color:#79C5FF; background:#142F52; }
            QToolButton#navButton { background: transparent; border: 0; border-radius: 10px; }
            QToolButton#navButton:hover { background: #1B3152; }
            QToolButton#navButton:checked { background: #2367BC; }
            QToolButton#navButton QLabel { background: transparent; color: #B6C7E0; font-size: 14px; }
            QToolButton#navButton:checked QLabel { color: #FFFFFF; font-weight: bold; }
            QPushButton { color: #DDEBFF; background: #1A3455; border: 1px solid #315C86;
                padding: 10px 13px; border-radius: 9px; }
            QPushButton:hover { background: #27568B; }
            QPushButton#primaryButton { background: #227AEB; border: 1px solid #4D9CFA; color: white; font-weight: bold; padding: 10px 22px; }
            QPushButton#primaryButton:hover { background: #358EFA; }
            QPushButton#secondaryButton { background: #1A2D47; }
            QPushButton#shapeCard { background:#11233B; border:1px solid #2A4A70; border-radius:12px; padding:8px; color:#CFE3FA; }
            QPushButton#shapeCard:checked { background:#1E4F8C; border:2px solid #6AB2FF; color:white; font-weight:bold; }
            QPushButton#langCard { font-size:20px; font-weight:bold; border-radius:14px; background:#11233B; }
            QPushButton#langCard:checked { background:#1E5FB0; border:2px solid #7BBEFF; }
            QFrame#footer { background: #0D1A2D; border-top: 1px solid #22385A; }
            QComboBox, QListWidget { background: #0F1E34; border: 1px solid #345476;
                border-radius: 9px; padding: 8px; color: #E9F3FF; selection-background-color: #236FCE; }
            QComboBox QAbstractItemView { background:#10233C; color:#E9F3FF; }
            QListWidget::item { padding: 8px; border-radius: 6px; }
            QListWidget::item:hover { background: #1D3656; }
            QCheckBox, QRadioButton { spacing: 10px; }
            QWidget#optionRow, QLabel#optionLabel { background: transparent; }
            QScrollArea { border: 0; background: #091729; }
        ''' + i18n.slider_css()).replace('SIDE', side).replace('SPACING', '0px' if i18n.is_rtl() else '1px')
           .replace('OVER', '12' if i18n.is_rtl() else '11'))


def _actions_for_profile(profile, supported_actions):
    """Every tool Morphix supports for a file-type profile (so users can add more)."""
    import tempfile, os
    kind, _, count = profile.partition('_')
    ext = {'pdf': '.pdf', 'image': '.png', 'video': '.mp4', 'audio': '.mp3', 'office': '.docx'}.get(kind)
    if not ext:
        return []
    n = 2 if count == 'multi' else 1
    tmp = tempfile.mkdtemp(prefix='morphix_prof_')
    paths = []
    try:
        for i in range(n):
            p = os.path.join(tmp, f'f{i}{ext}')
            open(p, 'wb').close()
            paths.append(p)
        return supported_actions(paths)
    finally:
        for p in paths:
            os.unlink(p)
        os.rmdir(tmp)
