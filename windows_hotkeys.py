"""Layout-independent Windows shortcuts using physical hardware scan codes.

Registers a WH_KEYBOARD_LL hook on a dedicated Windows message-loop thread.
Unlike character-based listeners, it never reads typed text; it compares
only scan codes and modifier key state, triggering the selected combination.
"""
from __future__ import annotations
import threading
import sys
from shortcut_logic import normalize_shortcut, is_valid_shortcut

# ANSI QWERTY physical scan positions, independent of selected input language.
SCAN_CODES = {
    'q':0x10,'w':0x11,'e':0x12,'r':0x13,'t':0x14,'y':0x15,'u':0x16,'i':0x17,'o':0x18,'p':0x19,
    'a':0x1e,'s':0x1f,'d':0x20,'f':0x21,'g':0x22,'h':0x23,'j':0x24,'k':0x25,'l':0x26,
    'z':0x2c,'x':0x2d,'c':0x2e,'v':0x2f,'b':0x30,'n':0x31,'m':0x32,
    '1':0x02,'2':0x03,'3':0x04,'4':0x05,'5':0x06,'6':0x07,'7':0x08,'8':0x09,'9':0x0a,'0':0x0b,
    'f1':0x3b,'f2':0x3c,'f3':0x3d,'f4':0x3e,'f5':0x3f,'f6':0x40,'f7':0x41,
    'f8':0x42,'f9':0x43,'f10':0x44,'f11':0x57,'f12':0x58,
    'backspace':0x0e,'tab':0x0f,'return':0x1c,'enter':0x1c,'space':0x39,
    'delete':0x53,'insert':0x52,'home':0x47,'end':0x4f,'pageup':0x49,'pagedown':0x51,
    'up':0x48,'down':0x50,'left':0x4b,'right':0x4d,
}


def parse_shortcut(shortcut):
    shortcut = normalize_shortcut(shortcut)
    if not is_valid_shortcut(shortcut):
        raise ValueError('Use a modifier plus a physical key.')
    parts = shortcut.split('+')
    modifiers = {p for p in parts if p in ('<cmd>','<ctrl>','<alt>','<shift>')}
    key = next(p.strip('<>') for p in parts if p not in modifiers)
    if key not in SCAN_CODES:
        raise ValueError('This physical key is not available on the current Windows build.')
    return modifiers, SCAN_CODES[key]


class WindowsGlobalHotkey:
    """Global shortcut for Windows.

    Primary: RegisterHotKey — the system delivers WM_HOTKEY to our thread, it
    works with any keyboard language (the key is mapped from its physical scan
    code), it is never silently removed, and it reports a clash when another
    program already owns the combination.
    Fallback: a WH_KEYBOARD_LL hook, only when RegisterHotKey is refused for a
    reason other than a clash. Windows removes low-level hooks whose callback is
    slow, which is why the hook is no longer the default.
    """
    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
    HOTKEY_ID = 0x4D58  # 'MX'

    def __init__(self, shortcut, callback):
        self.modifiers, self.scan = parse_shortcut(shortcut)
        self.shortcut = shortcut
        self.callback = callback
        self.mode = None
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self._error = None
        self._last_fire = 0.0

    def start(self):
        if sys.platform != 'win32':
            raise RuntimeError('Windows keyboard hook requires Windows.')
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name='Morphix Windows Hotkey', daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            raise RuntimeError('Windows global keyboard monitor did not start.')
        if self._error:
            raise RuntimeError(str(self._error))

    def _fire(self):
        import time
        now = time.monotonic()
        if now - self._last_fire < 0.35:   # ignore auto-repeat / double delivery
            return
        self._last_fire = now
        try:
            self.callback()
        except Exception as error:
            print('[Morphix Windows Hotkey]', error, flush=True)

    def _run(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        user32.MapVirtualKeyW.restype = wintypes.UINT
        WM_HOTKEY = 0x0312
        self._thread_id = kernel32.GetCurrentThreadId()
        hook = None
        hook_cb = None
        registered = False
        try:
            mods = self.MOD_NOREPEAT
            for name, flag in (('<alt>', self.MOD_ALT), ('<ctrl>', self.MOD_CONTROL),
                               ('<shift>', self.MOD_SHIFT), ('<cmd>', self.MOD_WIN)):
                if name in self.modifiers:
                    mods |= flag
            vk = user32.MapVirtualKeyW(self.scan, 3)   # MAPVK_VSC_TO_VK_EX
            if self.scan in EXTENDED_VK:
                vk = EXTENDED_VK[self.scan]
            if vk and user32.RegisterHotKey(None, self.HOTKEY_ID, mods, vk):
                registered = True
                self.mode = 'RegisterHotKey'
            else:
                err = ctypes.get_last_error()
                if err == 1409:   # ERROR_HOTKEY_ALREADY_REGISTERED
                    raise RuntimeError('ALREADY_REGISTERED')
                print(f'[Morphix Windows Hotkey] RegisterHotKey failed ({err}); using keyboard hook.', flush=True)
                hook, hook_cb = self._install_hook(user32, kernel32, ctypes, wintypes)
                self.mode = 'hook'
            self._ready.set()
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                    self._fire()
                    continue
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as error:
            self._error = error
            self._ready.set()
        finally:
            if registered:
                user32.UnregisterHotKey(None, self.HOTKEY_ID)
            if hook:
                user32.UnhookWindowsHookEx(hook)
            self._thread_id = None
            del hook_cb

    def _install_hook(self, user32, kernel32, ctypes, wintypes):
        WH_KEYBOARD_LL, HC_ACTION = 13, 0
        WM_KEYDOWN, WM_SYSKEYDOWN = 0x100, 0x104
        vk = {'<shift>': 0x10, '<ctrl>': 0x11, '<alt>': 0x12}

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD),
                        ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                        ('dwExtraInfo', ctypes.c_size_t)]
        CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, CALLBACK, wintypes.HINSTANCE, wintypes.DWORD]
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        def down(code):
            return bool(user32.GetAsyncKeyState(code) & 0x8000)

        def hook_callback(ncode, wparam, lparam):
            try:
                if ncode == HC_ACTION and wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    kb = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if kb.scanCode == self.scan:
                        actual = {key for key, value in vk.items() if down(value)}
                        if down(0x5b) or down(0x5c):
                            actual.add('<cmd>')
                        if actual == self.modifiers:
                            # Leave the hook immediately; run the callback later.
                            threading.Thread(target=self._fire, daemon=True).start()
            except Exception as error:
                print('[Morphix Windows Hotkey]', error, flush=True)
            return user32.CallNextHookEx(None, ncode, wparam, lparam)
        hook_cb = CALLBACK(hook_callback)
        hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_cb, kernel32.GetModuleHandleW(None), 0)
        if not hook:
            raise OSError(ctypes.get_last_error(), 'SetWindowsHookExW failed')
        return hook, hook_cb

    def stop(self):
        if self._thread_id and sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x12, 0, 0)
            if self._thread and threading.current_thread() is not self._thread:
                self._thread.join(timeout=1.5)


# Navigation keys share scan codes with the number pad; use their dedicated VKs.
EXTENDED_VK = {0x53: 0x2E, 0x52: 0x2D, 0x47: 0x24, 0x4f: 0x23, 0x49: 0x21, 0x51: 0x22,
               0x48: 0x26, 0x50: 0x28, 0x4b: 0x25, 0x4d: 0x27}
