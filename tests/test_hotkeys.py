"""No GUI or AppKit installation required for these structural tests."""
import sys
import threading
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_hotkeys import MacGlobalHotkey, parse_shortcut, MODIFIER_FLAGS


def test_parse_shortcut():
    flags, key = parse_shortcut('<cmd>+<shift>+m')
    assert flags == MODIFIER_FLAGS['<cmd>'] | MODIFIER_FLAGS['<shift>']
    assert key == 'm'
    assert parse_shortcut('<alt>+m')[1] == 'm'


def test_hotkey_matching_with_mocked_appkit(monkeypatch):
    class Event:
        def __init__(self, mods, code, text):
            self.mods, self.code, self.text = mods, code, text
        def modifierFlags(self):
            return self.mods
        def keyCode(self):
            return self.code
        def charactersIgnoringModifiers(self):
            return self.text
    class NSEvent:
        monitor = None
        @classmethod
        def addGlobalMonitorForEventsMatchingMask_handler_(cls, mask, handler):
            cls.monitor = handler
            return object()
        @classmethod
        def removeMonitor_(cls, observer):
            cls.monitor = None
    monkeypatch.setitem(sys.modules, 'AppKit', types.SimpleNamespace(NSEvent=NSEvent, NSEventMaskKeyDown=1))
    found = []
    shortcut = MacGlobalHotkey('<cmd>+<shift>+m', lambda: found.append('fired'))
    shortcut.start()
    # The physical M key works when Arabic/Urdu is the active input language.
    NSEvent.monitor(Event(shortcut.modifiers, 46, 'م'))
    NSEvent.monitor(Event(shortcut.modifiers, 7, 'x'))
    NSEvent.monitor(Event(MODIFIER_FLAGS['<shift>'], 46, 'm'))
    assert found == ['fired']
    shortcut.stop()
    assert NSEvent.monitor is None
