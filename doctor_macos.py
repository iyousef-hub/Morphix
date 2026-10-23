
"""Diagnose the macOS PySide6 Cocoa plugin for Morphix without starting the GUI."""
from __future__ import annotations
import importlib.util
import os
import pathlib
import platform
import sys

print("Morphix Qt diagnostics")
print("Python:", sys.executable)
print("Version:", sys.version.split()[0])
print("Platform:", platform.platform())
print("Virtual env:", sys.prefix != sys.base_prefix)
print("Conda active:", bool(os.environ.get("CONDA_PREFIX")))
for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_PLATFORM", "PYTHONPATH"):
    print(f"{name}:", os.environ.get(name, "<unset>"))
spec = importlib.util.find_spec("PySide6")
if spec is None or not spec.submodule_search_locations:
    print("ERROR: PySide6 not found in this Python. Run: python -m pip install -r requirements.txt")
    sys.exit(2)
base = pathlib.Path(next(iter(spec.submodule_search_locations)))
cocoa = base / "Qt" / "plugins" / "platforms" / "libqcocoa.dylib"
print("PySide6 directory:", base)
print("Cocoa plugin:", cocoa)
print("Cocoa exists:", cocoa.is_file())
if not cocoa.is_file():
    print("MISSING: Reinstall PySide6-Essentials and Shiboken inside the active .venv.")
    sys.exit(3)
try:
    from PySide6.QtCore import QLibraryInfo
    print("Qt default plugin directory:", QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
except Exception as e:
    print("Qt load ERROR:", repr(e))
    sys.exit(4)
print("Cocoa plugin is present. If the GUI still aborts, check for Anaconda or Qt binary conflicts.")
