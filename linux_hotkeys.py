"""Global shortcut on Linux.

* X11: grabs the key combination with XGrabKey (physical keycode, so it works
  with an Arabic or English keyboard layout), on a background thread.
* Wayland (and any desktop where grabbing is not possible): GNOME / Cinnamon /
  MATE get a system keyboard shortcut that runs `Morphix --hotkey`; on other
  desktops the user adds that command as a custom shortcut once.
"""
from __future__ import annotations

import os
import threading

from shortcut_logic import normalize_shortcut, is_valid_shortcut

MODIFIERS = {'<ctrl>': 'ControlMask', '<shift>': 'ShiftMask', '<alt>': 'Mod1Mask', '<cmd>': 'Mod4Mask'}
KEY_NAMES = {'enter': 'Return', 'return': 'Return', 'space': 'space', 'tab': 'Tab', 'backspace': 'BackSpace',
             'delete': 'Delete', 'insert': 'Insert', 'home': 'Home', 'end': 'End', 'pageup': 'Prior',
             'pagedown': 'Next', 'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right'}


def parse_shortcut(shortcut):
    shortcut = normalize_shortcut(shortcut)
    if not is_valid_shortcut(shortcut):
        raise ValueError('Use a modifier plus a physical key.')
    parts = shortcut.split('+')
    mods = [p for p in parts if p in MODIFIERS]
    key = next(p.strip('<>') for p in parts if p not in MODIFIERS)
    return mods, key


def session_type():
    return (os.environ.get('XDG_SESSION_TYPE') or ('wayland' if os.environ.get('WAYLAND_DISPLAY') else 'x11')).lower()


def gnome_binding(shortcut):
    """'<ctrl>+<shift>+m' → '<Control><Shift>m' (GNOME accelerator syntax)."""
    mods, key = parse_shortcut(shortcut)
    names = {'<ctrl>': '<Control>', '<shift>': '<Shift>', '<alt>': '<Alt>', '<cmd>': '<Super>'}
    key = KEY_NAMES.get(key, key)
    return ''.join(names[m] for m in mods) + key


class X11GlobalHotkey:
    mode = 'X11 key grab'

    def __init__(self, shortcut, callback):
        self.mods, self.key = parse_shortcut(shortcut)
        self.callback = callback
        self._thread = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._error = None
        self._display = None

    def start(self):
        if session_type() != 'x11' or not os.environ.get('DISPLAY'):
            raise RuntimeError('NO_X11')
        self._thread = threading.Thread(target=self._run, name='Morphix X11 Hotkey', daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            raise RuntimeError('The X11 keyboard shortcut did not start.')
        if self._error:
            raise RuntimeError(str(self._error))

    def _run(self):
        try:
            from Xlib import X, XK, display, error
            d = display.Display()
            self._display = d
            root = d.screen().root
            keysym = XK.string_to_keysym(KEY_NAMES.get(self.key, self.key))
            if not keysym and len(self.key) == 1:
                keysym = ord(self.key.lower())
            keycode = d.keysym_to_keycode(keysym)
            if not keycode:
                raise RuntimeError(f'Unknown key: {self.key}')
            mask = 0
            for m in self.mods:
                mask |= getattr(X, MODIFIERS[m])
            caught = []
            def on_error(err, *_):
                caught.append(err)
            # Also grab with Caps Lock / Num Lock on, or the shortcut stops working when they are.
            for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                root.grab_key(keycode, mask | extra, True, X.GrabModeAsync, X.GrabModeAsync, onerror=on_error)
            d.sync()
            if caught:
                raise RuntimeError('ALREADY_REGISTERED')
            self._ready.set()
            while not self._stop.is_set():
                if d.pending_events():
                    event = d.next_event()
                    if event.type == X.KeyPress and event.detail == keycode:
                        self.callback()
                else:
                    self._stop.wait(0.05)
            for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                root.ungrab_key(keycode, mask | extra)
            d.close()
        except Exception as exc:
            self._error = exc
            self._ready.set()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)


class DesktopShortcut:
    """Wayland / no X11: ask the desktop to run `Morphix --hotkey` on the shortcut."""
    mode = 'desktop keyboard shortcut'

    def __init__(self, shortcut, callback):
        self.shortcut = shortcut
        self.callback = callback  # the desktop runs the command; the IPC message calls back

    def start(self):
        import linux_integration
        if not linux_integration.register_desktop_shortcut(self.shortcut):
            raise RuntimeError('MANUAL_SHORTCUT')

    def stop(self):
        pass


def create(shortcut, callback):
    """The best available global shortcut for this Linux session."""
    if session_type() == 'x11' and os.environ.get('DISPLAY'):
        try:
            import Xlib  # noqa: F401
            return X11GlobalHotkey(shortcut, callback)
        except ImportError:
            pass
    return DesktopShortcut(shortcut, callback)
