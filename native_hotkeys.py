"""Main-thread macOS global shortcut monitor for Morphix.

NSGlobalEventMonitor is registered on the Qt/AppKit main thread, avoiding the
background Carbon input-source calls that crashed the v0.6 pynput listener on
macOS 27. The monitor intentionally observes only key-down events; it does not
capture, store, or transmit typed text.

Requires pyobjc-framework-Cocoa on macOS. macOS may request Input Monitoring or
Accessibility permission for the running Python/Terminal app.
"""
from __future__ import annotations

import re
import threading

MODIFIER_FLAGS = {
    '<cmd>': 1 << 20,    # NSEventModifierFlagCommand
    '<shift>': 1 << 17,  # NSEventModifierFlagShift
    '<alt>': 1 << 19,    # NSEventModifierFlagOption
    '<ctrl>': 1 << 18,   # NSEventModifierFlagControl
}
MODIFIER_MASK = sum(MODIFIER_FLAGS.values())


def parse_shortcut(shortcut: str):
    """Return (modifier_mask, key), or raise ValueError for unsupported format."""
    items = shortcut.lower().replace(' ', '').split('+')
    if not 2 <= len(items) <= 5 or len(items) != len(set(items)):
        raise ValueError('Shortcut must include a modifier and one key.')
    keys = [item for item in items if item not in MODIFIER_FLAGS]
    from shortcut_logic import is_valid_shortcut
    if not is_valid_shortcut(shortcut):
        raise ValueError('Unsupported shortcut key.')
    flags = 0
    for item in items:
        if item in MODIFIER_FLAGS:
            flags |= MODIFIER_FLAGS[item]
    if not flags:
        raise ValueError('At least one modifier is required.')
    return flags, keys[0]


# ANSI physical key positions as macOS virtual hardware key codes. This deliberately
# bypasses event.charactersIgnoringModifiers(), which changes with input language.
# A custom letter shortcut always refers to the same physical key position.
PHYSICAL_KEYS = {
    'a':0, 's':1, 'd':2, 'f':3, 'h':4, 'g':5, 'z':6, 'x':7,
    'c':8, 'v':9, 'b':11, 'q':12, 'w':13, 'e':14, 'r':15,
    'y':16, 't':17, '1':18, '2':19, '3':20, '4':21, '6':22,
    '5':23, '9':25, '7':26, '8':28, '0':29, 'o':31, 'u':32,
    'i':34, 'p':35, 'l':37, 'j':38, 'k':40, 'n':45, 'm':46,
    'f1':122, 'f2':120, 'f3':99, 'f4':118, 'f5':96, 'f6':97,
    'f7':98, 'f8':100, 'f9':101, 'f10':109, 'f11':103, 'f12':111,
    'f13':105, 'f14':107, 'f15':113, 'f16':106, 'f17':64, 'f18':79, 'f19':80, 'f20':90,
    'backspace':51, 'delete':117, 'tab':48, 'space':49, 'return':36,
    'enter':76, 'up':126, 'down':125, 'left':123, 'right':124,
    'home':115, 'end':119, 'pageup':116, 'pagedown':121,
}


def matches_event(event, modifiers, key):
    if (int(event.modifierFlags()) & MODIFIER_MASK) != modifiers:
        return False
    normalized = key.strip('<>')
    code = PHYSICAL_KEYS.get(normalized)
    return code is not None and int(event.keyCode()) == code


class MacGlobalHotkey:
    """Register an NSEvent keyDown global monitor from the main application thread."""

    def __init__(self, shortcut: str, callback):
        self.modifiers, self.key = parse_shortcut(shortcut)
        self.callback = callback
        self._monitor = None
        self._handler = None
        self._local_monitor = None
        self._local_handler = None

    def start(self):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Mac hotkey registration must run on the main thread.')
        if self._monitor is not None:
            return
        from AppKit import NSEvent, NSEventMaskKeyDown
        # Retain the handler for the lifetime of the native observer.
        self._handler = self._key_down
        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, self._handler
        )
        if self._monitor is None:
            self._handler = None
            raise RuntimeError('macOS refused the keyboard event monitor. Check Input Monitoring permissions.')
        # A global monitor does not receive events while our app is frontmost.
        self._local_handler = self._key_down_local
        add_local = getattr(NSEvent, 'addLocalMonitorForEventsMatchingMask_handler_', None)
        if add_local is not None:
            self._local_monitor = add_local(NSEventMaskKeyDown, self._local_handler)

    def _key_down(self, event):
        try:
            if matches_event(event, self.modifiers, self.key) and not bool(getattr(event, 'isARepeat', lambda: False)()):
                self.callback()
        except Exception as exc:
            # Never propagate exceptions into AppKit's native event dispatch.
            print(f'[Morphix hotkey] {exc}')

    def _key_down_local(self, event):
        self._key_down(event)
        return event

    def stop(self):
        if self._monitor is None and self._local_monitor is None:
            return
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('Mac hotkey removal must run on the main thread.')
        from AppKit import NSEvent
        if self._monitor is not None:
            NSEvent.removeMonitor_(self._monitor)
        if self._local_monitor is not None:
            NSEvent.removeMonitor_(self._local_monitor)
        self._monitor = None
        self._handler = None
        self._local_monitor = None
        self._local_handler = None


def accessibility_trusted(prompt=False):
    """True/False whether macOS lets this app observe global key presses.

    NSEvent global key monitors install fine without permission but receive
    NOTHING. With prompt=True macOS shows its own "Morphix would like to
    control this computer" sheet and adds Morphix to Settings → Accessibility.
    Returns None when the state cannot be determined (never nags then).
    """
    import sys
    if sys.platform != 'darwin':
        return None
    try:
        import ctypes
        services = ctypes.cdll.LoadLibrary(
            '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        if not prompt:
            services.AXIsProcessTrusted.restype = ctypes.c_bool
            return bool(services.AXIsProcessTrusted())
        cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        key = ctypes.c_void_p.in_dll(services, 'kAXTrustedCheckOptionPrompt')
        true = ctypes.c_void_p.in_dll(cf, 'kCFBooleanTrue')
        keys = (ctypes.c_void_p * 1)(key.value)
        values = (ctypes.c_void_p * 1)(true.value)
        cf.CFDictionaryCreate.restype = ctypes.c_void_p
        cf.CFDictionaryCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p]
        options = cf.CFDictionaryCreate(
            None, keys, values, 1,
            ctypes.addressof(ctypes.c_byte.in_dll(cf, 'kCFTypeDictionaryKeyCallBacks')),
            ctypes.addressof(ctypes.c_byte.in_dll(cf, 'kCFTypeDictionaryValueCallBacks')))
        services.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
        services.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        trusted = bool(services.AXIsProcessTrustedWithOptions(options))
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        if options:
            cf.CFRelease(options)
        return trusted
    except Exception as exc:
        print(f'[Morphix hotkey] Accessibility check unavailable: {exc}', flush=True)
        return None


def open_accessibility_settings():
    import subprocess
    subprocess.Popen(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'])
