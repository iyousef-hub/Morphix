"""macOS Qt/Cocoa start-up guard.

Do not allow a detached Morphix Studio process to abort without a clear
explanation when libqcocoa.dylib is missing from the active Python runtime.
The checks in this module avoid importing QtWidgets / creating an NSApplication.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import stat
from pathlib import Path

ENV_OVERRIDES = (
    'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_QPA_PLATFORM',
    'QT_QPA_PLATFORMTHEME', 'QT_QPA_FONTDIR', 'QT_QPA_GENERIC_PLUGINS',
    'DYLD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH', 'PYTHONPATH',
)


def clean_qt_environment(source=None):
    """Build a clean subprocess environment without stale Conda/Qt overrides."""
    env = dict(os.environ if source is None else source)
    for key in ENV_OVERRIDES:
        env.pop(key, None)
    return env


def cocoa_plugin_path(pyside_dir=None):
    if pyside_dir is None:
        spec = importlib.util.find_spec('PySide6')
        if spec is None or not spec.submodule_search_locations:
            return None
        pyside_dir = Path(next(iter(spec.submodule_search_locations)))
    return Path(pyside_dir) / 'Qt' / 'plugins' / 'platforms' / 'libqcocoa.dylib'


def restore_hidden_qt_plugins(plugin_root):
    """Clear macOS UF_HIDDEN only within the selected PySide6 install.

    With UF_HIDDEN set, Python can see the dylib and QPluginLoader can read its
    metadata, but Qt's regular QDir plugin scan excludes it. This produced the
    reproducible `Could not find the Qt platform plugin` abort on this Mac.
    """
    plugin_root = Path(plugin_root)
    if not plugin_root.is_dir():
        return []
    flag = getattr(stat, 'UF_HIDDEN', 0)
    if not flag or sys.platform != 'darwin':
        return []
    changed = []
    for path in plugin_root.rglob('*.dylib'):
        try:
            st = path.stat()
            if st.st_flags & flag:
                os.chflags(path, st.st_flags & ~flag)
                changed.append(path)
        except OSError as exc:
            raise RuntimeError(f'Unable to unhide Qt plugin: {path}: {exc}') from exc
    return changed


def configure_qt_macos():
    """Run before importing PySide6.QtWidgets in both Studio and helper."""
    if sys.platform != 'darwin':
        return None
    if getattr(sys, 'frozen', False):
        # PyInstaller's Qt hook configures plugins in its _MEIPASS bundle.
        # Do not force source-venv paths inside a packaged .app.
        return None
    plugin = cocoa_plugin_path()
    if plugin is None or not plugin.is_file():
        label = str(plugin) if plugin is not None else 'PySide6 is not installed'
        raise RuntimeError(
            'Morphix cannot start the macOS interface: Qt Cocoa plugin missing.\n'
            f'Python: {sys.executable}\nCocoa: {label}\n'
            'Try running zsh ./Launch_Morphix_Mac.command from the Morphix folder.\n'
            'For details, run: runtime/bin/python doctor_qt_macos.py'
        )
    # Qt's macOS QDir ignores dylibs flagged UF_HIDDEN (even if QPluginLoader
    # metadata is valid). Fix the user's project-local PySide6 installation
    # before QtWidgets creates QApplication.
    changed = restore_hidden_qt_plugins(plugin.parent.parent)
    if changed:
        print(f'[Morphix Qt] Restored {len(changed)} hidden plugin(s).', flush=True)
    # Qt may have loaded QtCore from this exact venv; choose its own platforms.
    for key in ENV_OVERRIDES:
        os.environ.pop(key, None)
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugin.parent)
    return plugin
