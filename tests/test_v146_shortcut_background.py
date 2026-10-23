"""Tests run on Linux without Qt, ensuring hotkey core remains portable."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shortcut_logic import is_valid_shortcut, display_shortcut, make_shortcut
from native_hotkeys import matches_event, parse_shortcut, PHYSICAL_KEYS
from windows_hotkeys import parse_shortcut as parse_windows, SCAN_CODES


def test_custom_capture_format_and_physical_key():
    shortcut = make_shortcut({'<ctrl>', '<shift>'}, '<delete>')
    assert shortcut == '<ctrl>+<shift>+<delete>'
    assert is_valid_shortcut(shortcut)
    assert display_shortcut(shortcut, True) == 'Ctrl + Shift + Del'
    assert display_shortcut(shortcut, False) == 'Ctrl + Shift + Del'
    assert parse_shortcut(shortcut)[1] == '<delete>'
    assert PHYSICAL_KEYS['delete'] == 117
    assert parse_windows(shortcut) == ({'<ctrl>', '<shift>'}, 0x53)


def test_layout_independent_macos_keys():
    mods, key = parse_shortcut('<cmd>+<shift>+m')
    class MockEvent:
        def modifierFlags(self):return mods
        def keyCode(self):return 46
        def charactersIgnoringModifiers(self):return 'م'
    assert matches_event(MockEvent(), mods, key)


def test_allowed_and_unsupported_shortcuts():
    assert is_valid_shortcut('<alt>+m')
    assert is_valid_shortcut('<cmd>+<shift>+<f12>')
    assert not is_valid_shortcut('<ctrl>')
    assert not is_valid_shortcut('m')
    assert not is_valid_shortcut('<ctrl>+<shift>')
    assert not is_valid_shortcut('<ctrl>+<shift>+m+n')


def test_windows_physical_us_scan_positions():
    assert SCAN_CODES['m'] == 0x32
    assert SCAN_CODES['a'] == 0x1e
    assert parse_windows('<ctrl>+<shift>+m') == ({'<ctrl>','<shift>'},0x32)


def test_autostart_doesnt_install_itself():
    import autostart
    args = autostart._launch_args()
    assert '--background' in args
    assert 'main.py' in ' '.join(args)
