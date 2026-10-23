"""Isolated Morphix Studio host.

The always-on Quick Wheel process stays an AppKit *accessory* application.  Studio
runs in its own Qt process as a normal, focusable desktop application.  This
avoids dynamically switching NSApplication activation policy on live Qt windows,
which can leave a visible macOS window unable to receive mouse events.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def studio_socket_name(home=None):
    home = Path.home() if home is None else Path(home)
    return 'morphix-studio-' + hashlib.sha256(str(home.resolve()).encode('utf-8')).hexdigest()[:18]


def encode_studio_message(paths=None, command='raise', page=0):
    return json.dumps({'command': command, 'page': int(page), 'paths': [str(p) for p in (paths or [])]}, ensure_ascii=False).encode('utf-8')


def decode_studio_message(payload):
    message = json.loads(bytes(payload).decode('utf-8'))
    if not isinstance(message, dict) or message.get('command') not in ('raise', 'preferences'):
        raise ValueError('Unsupported Studio IPC command')
    paths = message.get('paths', [])
    if not isinstance(paths, list) or len(paths) > 2000 or any(not isinstance(p, str) for p in paths):
        raise ValueError('Invalid Studio file list')
    page = message.get('page', 0)
    if type(page) is not int or page < 0 or page > 10:
        raise ValueError('Invalid preferences page')
    return message['command'], page, [p for p in paths if Path(p).is_file()]


def studio_start_args(executable, main_path, frozen=False, paths=None, command='raise', page=0):
    """PyInstaller routes Studio to the same app binary via --studio-window."""
    args = ([str(executable)] if frozen else [str(executable), str(main_path)]) + ['--studio-window']
    if paths:
        args += ['--initial-paths', json.dumps([str(p) for p in paths], ensure_ascii=False)]
    if command == 'preferences':
        args += ['--studio-preferences', str(page)]
    return args


def start_studio_process(executable, main_path, frozen=False, paths=None, command='raise', page=0):
    """Spawn Studio with isolated Qt paths and a permanent crash log.

    A prior QProcess.startDetached() could return success even though Qt Studio
    aborted while loading the Cocoa plugin, leaving the menu action apparently
    unresponsive. We retain stderr in ~/Library/Logs/Morphix/studio.log.
    """
    import os
    import subprocess
    import sys
    from datetime import datetime
    from qt_macos_runtime import clean_qt_environment

    args = studio_start_args(executable, main_path, frozen, paths, command, page)
    if sys.platform == 'darwin':
        directory = Path.home() / 'Library' / 'Logs' / 'Morphix'
    elif os.name == 'nt':
        directory = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Morphix' / 'logs'
    else:
        directory = Path.home() / '.local' / 'state' / 'morphix'
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / 'studio.log'
    # Frozen/PyInstaller apps need their bootloader Qt/DYLD environment;
    # source venvs benefit from discarding inherited Anaconda Qt paths.
    env = dict(os.environ) if frozen else clean_qt_environment()
    env['PYTHONUNBUFFERED'] = '1'
    try:
        with log_path.open('a', encoding='utf-8') as output:
            output.write(f'\n--- Studio start {datetime.now().isoformat(timespec="seconds")} ---\n')
            output.flush()
            process = subprocess.Popen(args, cwd=str(Path(main_path).parent), env=env,
                                       stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT,
                                       start_new_session=(os.name != 'nt'))
    except OSError as exc:
        raise RuntimeError(f'Could not start Morphix Studio: {exc}. Log: {log_path}') from exc
    return process


def allow_foreground():
    """Windows only lets the process the user just clicked bring a window to
    the front. The tray/background process has that right right now, so it
    passes it on to the Studio process before asking it to show itself."""
    import sys
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)   # ASFW_ANY
    except Exception:
        pass


def bring_to_front(window):
    """Show, un-minimise and really bring a Qt window to the front on Windows."""
    import sys
    from PySide6.QtCore import Qt
    if window.windowState() & Qt.WindowMinimized:
        window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
    window.showNormal() if not window.isMaximized() else window.show()
    window.raise_()
    window.activateWindow()
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = int(window.winId())
        SW_RESTORE, HWND_TOPMOST, HWND_NOTOPMOST = 9, -1, -2
        SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = 0x2, 0x1, 0x40
        user32.ShowWindow(hwnd, SW_RESTORE)
        # Briefly topmost, then normal: reliably lifts it above other windows.
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.SetForegroundWindow(hwnd)
    except Exception as exc:
        print('[Morphix Studio] bring_to_front:', exc, flush=True)


def send_to_studio(paths=None, timeout=250, command='raise', page=0):
    from PySide6.QtNetwork import QLocalSocket
    sock = QLocalSocket()
    sock.connectToServer(studio_socket_name())
    if not sock.waitForConnected(timeout):
        return False
    sock.write(encode_studio_message(paths, command, page))
    sock.flush()
    sock.waitForBytesWritten(timeout)
    sock.disconnectFromServer()
    return True


class StudioController:
    """Only settings and Studio UI. No AppKit hotkey monitor in this process."""
    def __init__(self, window):
        from PySide6.QtCore import QSettings
        self.studio = window
        self.settings = QSettings('Morphix', 'Morphix')

    def open_preferences(self, page=0):
        from PySide6.QtWidgets import QDialog
        from wheel_preferences import WheelSettings
        from shortcut_logic import display_shortcut
        import platform
        import i18n
        from i18n import tr
        before = i18n.current()
        dlg = WheelSettings(self.settings, self.studio)
        if page:
            dlg._switch_page(page)
        if dlg.exec() == QDialog.Accepted:
            if i18n.chosen() and i18n.chosen() != before:
                self.restart_for_language()
                return
            # The background helper must reload its running hotkey on save.
            self.notify_background('reload-settings')
            if hasattr(self.studio, 'hero_shortcut'):
                hotkey = str(self.settings.value('shortcut', '<cmd>+<shift>+m' if platform.system() == 'Darwin' else '<ctrl>+<shift>+m'))
                self.studio.hero_shortcut.setText(tr('Select files anywhere, then press') + ' ' + display_shortcut(hotkey, platform.system() == 'Darwin'))

    def restart_for_language(self):
        """Language changed: restart Morphix (helper + Studio) in the new language."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        import i18n
        if not self.notify_background('restart', quiet=True):
            i18n.spawn_relaunch(delay=1.0)        # no helper running: restart ourselves
        QTimer.singleShot(100, QApplication.instance().quit)

    def open_wheel_settings(self):
        return self.open_preferences()

    def open_shortcuts(self):
        return self.open_preferences(page=2)

    def open_quick_wheel(self):
        paths = self.studio.selected_paths()
        if paths:
            self.notify_background('wheel-paths:' + json.dumps(paths, ensure_ascii=False))
        else:
            self.notify_background('wheel')

    def notify_background(self, command, quiet=False):
        from PySide6.QtNetwork import QLocalSocket
        import hashlib
        from PySide6.QtWidgets import QMessageBox
        name = 'morphix-one-' + hashlib.sha256(str(Path.home().resolve()).encode('utf-8')).hexdigest()[:18]
        sock = QLocalSocket()
        sock.connectToServer(name)
        if not sock.waitForConnected(250):
            if not quiet:
                from i18n import tr
                QMessageBox.information(self.studio, tr('Morphix'),
                    tr('Morphix is not running in the background. Open Morphix from your Applications folder.'))
            return False
        sock.write(command.encode('utf-8'))
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True

    def on_studio_hidden(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        # Closing Studio leaves the independent Quick Wheel process alive.
        QTimer.singleShot(0, QApplication.instance().quit)
