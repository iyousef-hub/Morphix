"""Terminal-only diagnostics for Morphix developers. No Qt window is opened."""
import os
import sys
from pathlib import Path
from runtime_guard import missing_modules

print('Morphix runtime diagnostic')
print('Python:', sys.executable)
print('Project:', Path(__file__).resolve().parent)
print('Virtual environment:', sys.prefix != sys.base_prefix)
print('Missing core packages:', ', '.join(missing_modules()) or '(none)')
try:
    import pymupdf
    print('PyMuPDF:', getattr(pymupdf, 'VersionBind', 'available'))
except Exception as e:
    print('PyMuPDF import failed:', e)
try:
    from PySide6.QtCore import __version__ as qt_version
    print('PySide6:', qt_version)
except Exception as e:
    print('PySide6 import failed:', e)
print('Run zsh ./Launch_Morphix_Mac.command to prepare and launch the project on macOS.')
