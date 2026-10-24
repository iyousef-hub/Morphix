"""Linux desktop integration (no root needed, everything in the user's home).

* An app-menu entry (Morphix in Activities / the application menu).
* "Morphix" in the right-click menu of Files (Nautilus), Nemo and Dolphin:
  it opens the Action Hub with the selected files.
* Reading files that were copied (Ctrl+C) in the file manager, so the global
  shortcut can work on Wayland too.
* A system keyboard shortcut on GNOME-style desktops (needed on Wayland).
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

HOME = Path.home()
DATA = Path(os.environ.get('XDG_DATA_HOME', HOME / '.local' / 'share'))
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))


def launch_command():
    """How to start this copy of Morphix from outside (AppImage, frozen or source)."""
    appimage = os.environ.get('APPIMAGE')
    if appimage and Path(appimage).is_file():
        return [appimage]
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).resolve())]
    return [sys.executable, str(Path(__file__).resolve().with_name('main.py'))]


def _cmd(*extra):
    return ' '.join(shlex.quote(p) for p in launch_command() + list(extra))


def _write(path: Path, text: str, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8', errors='replace') != text:
        path.write_text(text, encoding='utf-8')
    if executable:
        path.chmod(0o755)


def icon_path():
    from app_assets import ASSETS
    return ASSETS / 'morphix_logo.png'


def install(verbose=False):
    """Create / refresh the menu entry and the right-click actions. Safe to call on every start."""
    if not sys.platform.startswith('linux'):
        return []
    written = []
    icon_dst = DATA / 'icons' / 'hicolor' / '256x256' / 'apps' / 'morphix.png'
    try:
        src = icon_path()
        if src.is_file():
            icon_dst.parent.mkdir(parents=True, exist_ok=True)
            if not icon_dst.exists() or icon_dst.stat().st_size != src.stat().st_size:
                shutil.copyfile(src, icon_dst)
    except OSError:
        pass
    run = _cmd()
    hub = _cmd('--hub')
    desktop = (
        '[Desktop Entry]\nType=Application\nName=Morphix\n'
        'Comment=Every file tool you need — one shortcut away\n'
        'Comment[ar]=كل أدوات ملفاتك — باختصار واحد\n'
        f'Exec={run} --studio\nIcon=morphix\nTerminal=false\n'
        'Categories=Utility;Office;Graphics;\nKeywords=pdf;image;convert;compress;ocr;speech;\n'
        'StartupWMClass=Morphix\nActions=hub;\n\n'
        '[Desktop Action hub]\nName=Open files in the Action Hub\n'
        f'Exec={hub} %F\n')
    targets = {
        DATA / 'applications' / 'morphix.desktop': (desktop, False),
        # GNOME Files (Nautilus): right-click → Scripts → Morphix
        DATA / 'nautilus' / 'scripts' / 'Morphix': (f'#!/bin/sh\nexec {hub} "$@"\n', True),
        # Nemo (Linux Mint): right-click → Morphix
        DATA / 'nemo' / 'actions' / 'morphix.nemo_action': (
            '[Nemo Action]\nName=Morphix\nComment=Open the selected files in the Morphix Action Hub\n'
            f'Exec={hub} %F\nIcon-Name=morphix\nSelection=notnone\nExtensions=any;\n', False),
        # Dolphin (KDE): right-click → Morphix
        DATA / 'kio' / 'servicemenus' / 'morphix.desktop': (
            '[Desktop Entry]\nType=Service\nMimeType=application/octet-stream;all/allfiles;\n'
            'X-KDE-ServiceTypes=KonqPopupMenu/Plugin\nActions=morphix;\n\n'
            '[Desktop Action morphix]\nName=Morphix\nIcon=morphix\n'
            f'Exec={hub} %F\n', True),
    }
    for path, (text, executable) in targets.items():
        try:
            _write(path, text, executable)
            written.append(path)
        except OSError as exc:
            if verbose:
                print('[Morphix] Could not write', path, exc, flush=True)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(DATA / 'applications')],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return written


# ---------------------------------------------------------------- clipboard
def files_from_uri_text(text: str):
    files = []
    for line in (text or '').splitlines():
        line = line.strip()
        if not line or line in ('copy', 'cut') or line.startswith('#'):
            continue
        if line.startswith('file://'):
            path = unquote(urlparse(line).path)
        elif line.startswith('/'):
            path = line
        else:
            continue
        if Path(path).is_file():
            files.append(path)
    return files


def clipboard_files():
    """Files copied in the file manager (Ctrl+C) — the Linux 'selection'."""
    try:
        from PySide6.QtWidgets import QApplication
        mime = QApplication.clipboard().mimeData()
    except Exception:
        return []
    if mime is None:
        return []
    for fmt in ('x-special/gnome-copied-files', 'text/uri-list'):
        if mime.hasFormat(fmt):
            files = files_from_uri_text(bytes(mime.data(fmt)).decode('utf-8', 'replace'))
            if files:
                return files
    if mime.hasUrls():
        return [u.toLocalFile() for u in mime.urls() if u.isLocalFile() and Path(u.toLocalFile()).is_file()]
    return []


# ---------------------------------------------------------------- desktop shortcut
GNOME_KEYS = 'org.gnome.settings-daemon.plugins.media-keys'
GNOME_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/morphix/'


def _gsettings(*args):
    return subprocess.run(['gsettings', *args], capture_output=True, text=True, timeout=5)


def register_desktop_shortcut(shortcut):
    """GNOME (also Ubuntu, Pop!_OS, Zorin…): add a custom keyboard shortcut. Returns True on success."""
    if not shutil.which('gsettings'):
        return False
    try:
        from linux_hotkeys import gnome_binding
        current = _gsettings('get', GNOME_KEYS, 'custom-keybindings')
        if current.returncode:
            return False
        value = current.stdout.strip()
        paths = [] if value.startswith('@as') else [p.strip().strip("'") for p in value.strip('[]').split(',') if p.strip()]
        if GNOME_PATH not in paths:
            paths.append(GNOME_PATH)
            _gsettings('set', GNOME_KEYS, 'custom-keybindings', '[' + ', '.join(f"'{p}'" for p in paths) + ']')
        schema = f'{GNOME_KEYS}.custom-keybinding:{GNOME_PATH}'
        _gsettings('set', schema, 'name', 'Morphix — Action Hub')
        _gsettings('set', schema, 'command', _cmd('--hotkey'))
        done = _gsettings('set', schema, 'binding', gnome_binding(shortcut))
        return done.returncode == 0
    except Exception:
        return False


def manual_shortcut_command():
    return _cmd('--hotkey')
