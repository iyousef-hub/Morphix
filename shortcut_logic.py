"""Portable hotkey notation and human-readable labels for Morphix.

The stored format (<cmd>+<shift>+m) remains backward-compatible with the
existing macOS and Windows global shortcut configuration.
"""
from __future__ import annotations

import re

MODIFIERS = ('<cmd>', '<ctrl>', '<alt>', '<shift>')
SPECIAL_KEYS = {'delete', 'backspace', 'tab', 'space', 'return', 'enter',
                'up', 'down', 'left', 'right', 'home', 'end', 'pageup', 'pagedown',
                'insert'}
KEY_PATTERN = re.compile(r'(?:[a-z0-9]|<f(?:[1-9]|1[0-9]|20)>|<(?:' + '|'.join(sorted(SPECIAL_KEYS)) + r')>)\Z')
MAC_SYMBOLS = {'<cmd>': '⌘ Command', '<ctrl>': 'Ctrl', '<alt>': 'Option', '<shift>': 'Shift'}
WIN_SYMBOLS = {'<cmd>': 'Win', '<ctrl>': 'Ctrl', '<alt>': 'Alt', '<shift>': 'Shift'}
SPECIAL_LABELS = {
    'delete': 'Del', 'backspace': 'Backspace', 'tab': 'Tab', 'space': 'Space',
    'return': 'Return', 'enter': 'Enter', 'up': '↑', 'down': '↓', 'left': '←',
    'right': '→', 'home': 'Home', 'end': 'End', 'pageup': 'Page Up',
    'pagedown': 'Page Down', 'insert': 'Ins',
}


def normalize_shortcut(shortcut: str) -> str:
    return shortcut.strip().lower().replace(' ', '')


def is_valid_shortcut(shortcut: str) -> bool:
    parts = normalize_shortcut(shortcut).split('+')
    if not 2 <= len(parts) <= 5 or len(parts) != len(set(parts)):
        return False
    keys = [part for part in parts if part not in MODIFIERS]
    return len(keys) == 1 and len(keys[0]) > 0 and bool(KEY_PATTERN.fullmatch(keys[0])) and len(keys) < len(parts)


def display_shortcut(shortcut: str, mac: bool) -> str:
    names = MAC_SYMBOLS if mac else WIN_SYMBOLS
    parts = normalize_shortcut(shortcut).split('+')
    values = []
    for part in parts:
        if part in names:
            values.append(names[part])
        elif part.startswith('<') and part.endswith('>'):
            key = part[1:-1]
            values.append(SPECIAL_LABELS.get(key, key.upper()))
        else:
            values.append(part.upper())
    return ' + '.join(values)


def make_shortcut(modifiers, key):
    """Use stable modifier ordering when recording keyboard events."""
    pieces = [part for part in MODIFIERS if part in modifiers]
    pieces.append(key)
    return '+'.join(pieces)
