"""Click-to-record keyboard shortcuts; no OS-wide text/keystroke logging.

Only intercepts key events while this focused widget is recording. Letter keys
use macOS physical key codes instead of layout-dependent Unicode characters.
"""
from __future__ import annotations

import platform
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import QLineEdit
from i18n import tr
from shortcut_logic import (display_shortcut, is_valid_shortcut, make_shortcut,
                            MODIFIERS, normalize_shortcut)

MAC = platform.system() == 'Darwin'


def _qt_modifiers(mods):
    # On macOS Qt reports ⌘ Command as ControlModifier and the Control key as
    # MetaModifier. Without this swap a recorded ⌘⇧M was saved as Ctrl+Shift+M
    # and the global shortcut never fired.
    ctrl_flag, cmd_flag = (Qt.MetaModifier, Qt.ControlModifier) if MAC else (Qt.ControlModifier, Qt.MetaModifier)
    active = set()
    if mods & ctrl_flag:
        active.add('<ctrl>')
    if mods & Qt.ShiftModifier:
        active.add('<shift>')
    if mods & Qt.AltModifier:
        active.add('<alt>')
    if mods & cmd_flag:
        active.add('<cmd>')
    return active


def _key_name(event):
    # Qt nativeVirtualKey == NSEvent.keyCode on macOS; it remains the SAME key
    # under Arabic, Urdu, English and other input sources.
    if MAC:
        from native_hotkeys import PHYSICAL_KEYS
        native = int(event.nativeVirtualKey())
        inverse = {v: k for k, v in PHYSICAL_KEYS.items()}
        # QTest synthetic events often set nativeVirtualKey to zero; zero is
        # also the legitimate physical A key, so prefer Qt's special-key code
        # for synthetic Delete/Backspace/F-keys rather than mistaking it for A.
        qt_key = event.key()
        special_qt = qt_key in (
            Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_Tab, Qt.Key_Space,
            Qt.Key_Return, Qt.Key_Enter, Qt.Key_Up, Qt.Key_Down,
            Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End,
            Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Insert,
        ) or (Qt.Key_F1 <= qt_key <= Qt.Key_F20)
        if native in inverse and (native != 0 or not special_qt):
            name = inverse[native]
            return '<' + name + '>' if len(name) > 1 else name
    if platform.system() == 'Windows':
        from windows_hotkeys import SCAN_CODES
        scan = int(event.nativeScanCode()) & 0xff
        inverse = {v:k for k,v in SCAN_CODES.items()}
        if scan in inverse:
            name = inverse[scan]
            return '<' + name + '>' if len(name) > 1 else name
    key = event.key()
    specials = {
        Qt.Key_Delete: '<delete>', Qt.Key_Backspace: '<backspace>',
        Qt.Key_Tab: '<tab>', Qt.Key_Space: '<space>',
        Qt.Key_Return: '<return>', Qt.Key_Enter: '<enter>',
        Qt.Key_Up: '<up>', Qt.Key_Down: '<down>',
        Qt.Key_Left: '<left>', Qt.Key_Right: '<right>',
        Qt.Key_Home: '<home>', Qt.Key_End: '<end>',
        Qt.Key_PageUp: '<pageup>', Qt.Key_PageDown: '<pagedown>',
        Qt.Key_Insert: '<insert>',
    }
    if key in specials:
        return specials[key]
    if Qt.Key_F1 <= key <= Qt.Key_F20:
        return f'<f{key - Qt.Key_F1 + 1}>'
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key).lower()
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    # Qt's localized event.text() is intentionally not saved: translated
    # characters do not correspond to stable global physical shortcuts.
    return None


class ShortcutRecorder(QLineEdit):
    shortcutChanged = Signal(str)

    def __init__(self, shortcut, parent=None):
        # QWidget/QLineEdit configuration calls can deliver Qt events *inside*
        # the constructor (for example setReadOnly).  Our event() override must
        # never access a field that has not been initialized yet.
        self._recording = False
        self._saved = normalize_shortcut(shortcut)
        super().__init__(parent)
        self.setObjectName('shortcutRecorder')
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setAlignment(Qt.AlignCenter)
        self.setToolTip(tr('Click, then press a modifier and a key. Esc cancels.'))
        self._show_saved()

    def _show_saved(self):
        self.setText(display_shortcut(self._saved, MAC))

    def shortcut(self):
        return self._saved

    def start_recording(self):
        self._recording = True
        self.setProperty('recording', True)
        self.setText(tr('Press your shortcut…'))
        self.style().unpolish(self)
        self.style().polish(self)
        self.setFocus(Qt.MouseFocusReason)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.start_recording()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if getattr(self, '_recording', False):
            self._recording = False
            self.setProperty('recording', False)
            self._show_saved()
            self.style().unpolish(self)
            self.style().polish(self)

    def event(self, event):
        # Qt usually intercepts Tab for focus navigation before keyPressEvent.
        # The recorder must be allowed to capture it as a physical hotkey.
        if (getattr(self, '_recording', False) and event.type() == QEvent.KeyPress
                and event.key() in (Qt.Key_Tab, Qt.Key_Backtab)):
            self.keyPressEvent(event)
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if not getattr(self, '_recording', False):
            self.start_recording()
        if event.key() == Qt.Key_Escape:
            self.cancel()
            return
        modifiers = _qt_modifiers(event.modifiers())
        modifier_key = ({Qt.Key_Control: '<cmd>', Qt.Key_Meta: '<ctrl>'} if MAC else
                        {Qt.Key_Control: '<ctrl>', Qt.Key_Meta: '<cmd>'})
        modifier_key.update({Qt.Key_Shift: '<shift>', Qt.Key_Alt: '<alt>'})
        modifier_key = modifier_key.get(event.key())
        if modifier_key:
            modifiers.add(modifier_key)
            self.setText(' + '.join(
                display_shortcut(m, MAC) for m in MODIFIERS if m in modifiers
            ))
            return
        key = _key_name(event)
        if not key:
            self.setText(tr('That key is not supported — try a letter, Delete or an F-key'))
            return
        candidate = make_shortcut(modifiers, key)
        if not is_valid_shortcut(candidate):
            self.setText(tr('Hold ⌘ / Ctrl / Option / Shift, then press a key'))
            return
        self._saved = candidate
        self._recording = False
        self.setProperty('recording', False)
        self._show_saved()
        self.shortcutChanged.emit(candidate)
        self.style().unpolish(self)
        self.style().polish(self)
        self.clearFocus()

    def cancel(self):
        self._recording = False
        self.setProperty('recording', False)
        self._show_saved()
        self.clearFocus()

    def clear_shortcut(self, default):
        self._saved = normalize_shortcut(default)
        self._show_saved()
        self.shortcutChanged.emit(self._saved)
