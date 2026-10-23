#!/usr/bin/env python3
"""Inspect a Morphix macOS Qt installation without crashing the GUI.

Run from project folder: .venv/bin/python doctor_qt_macos.py
Repair missing Cocoa with: .venv/bin/python doctor_qt_macos.py --repair
"""
from __future__ import annotations
import os
import sys
import stat
import subprocess
from pathlib import Path
import importlib.metadata as metadata
from qt_macos_runtime import cocoa_plugin_path, clean_qt_environment, restore_hidden_qt_plugins


def diagnosis():
    plugin = cocoa_plugin_path()
    plugin_dir = plugin.parent if plugin is not None else None
    print('Morphix macOS Qt/Cocoa diagnostics', flush=True)
    print('Python:', sys.executable, flush=True)
    print('sys.prefix:', sys.prefix, flush=True)
    print('Conda active:', bool(os.environ.get('CONDA_PREFIX')), flush=True)
    for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'PYTHONPATH', 'DYLD_LIBRARY_PATH'):
        print(f'{key}:', os.environ.get(key, '<unset>'), flush=True)
    try:
        version = metadata.version('PySide6-Essentials')
    except metadata.PackageNotFoundError:
        version = 'NOT INSTALLED'
    print('PySide6-Essentials:', version, flush=True)
    print('Platform plugins folder:', plugin_dir, flush=True)
    print('Cocoa dylib:', plugin, flush=True)
    available = plugin is not None and plugin.is_file()
    print('Cocoa exists:', available, flush=True)
    if available and sys.platform == 'darwin':
        print('Cocoa UF_HIDDEN:', bool(plugin.stat().st_flags & getattr(stat, 'UF_HIDDEN', 0)), flush=True)
    if plugin_dir and plugin_dir.is_dir():
        print('Platform plugin names:', sorted(p.name for p in plugin_dir.iterdir()), flush=True)
    if not available:
        print('Required plugin is missing from this Python environment.', flush=True)
    return available


def fix_hidden():
    plugin = cocoa_plugin_path()
    if plugin is None:
        print('No PySide6 installation detected.')
        return False
    changed = restore_hidden_qt_plugins(plugin.parent.parent)
    print('Qt plugin hidden flags cleared:', len(changed), flush=True)
    return diagnosis()


def repair():
    print('Reinstalling the official Qt runtime into THIS virtual environment...', flush=True)
    # Reinstall Essentials and matching Shiboken from a fresh index download.
    command = [sys.executable, '-m', 'pip', 'install', '--upgrade',
               '--force-reinstall', '--no-cache-dir', 'PySide6-Essentials>=6.7,<7']
    completed = subprocess.run(command, env=clean_qt_environment())
    if completed.returncode:
        return False
    return diagnosis()


def probe():
    """OPTIONAL real Cocoa load smoke-test in a child so Morphix stays alive."""
    plugin = cocoa_plugin_path()
    if plugin is None or not plugin.is_file():
        return diagnosis()
    env = clean_qt_environment()
    env['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugin.parent)
    env['QT_DEBUG_PLUGINS'] = '1'
    command = [sys.executable, '-c',
               'from PySide6.QtWidgets import QApplication; '
               'app = QApplication([]); print("Qt Cocoa GUI probe: SUCCESS", flush=True)']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=18, env=env)
    except subprocess.TimeoutExpired:
        print('Qt Cocoa probe timed out after 18 seconds.')
        return False
    print('Probe exit status:', result.returncode)
    if result.stdout.strip():
        print(result.stdout[-4000:])
    if result.returncode:
        print('Qt load diagnostic (last lines):')
        print('\n'.join(result.stderr.splitlines()[-45:]))
    return result.returncode == 0


if __name__ == '__main__':
    if '--probe' in sys.argv:
        sys.exit(0 if probe() else 3)
    if '--fix-hidden' in sys.argv:
        sys.exit(0 if fix_hidden() else 4)
    if '--repair' in sys.argv:
        sys.exit(0 if repair() else 2)
    sys.exit(0 if diagnosis() else 2)
