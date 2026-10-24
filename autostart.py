"""User-controlled launch-at-login (no elevated privileges, no background network).

macOS: per-user LaunchAgent. Windows: per-user HKCU Run key.
Linux: ~/.config/autostart/morphix.desktop (XDG autostart).
Never enables launch-at-login without an explicit settings checkbox selection.
"""
from __future__ import annotations
import os
import platform
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = 'com.yousef.morphix'


def _mac_plist():
    return Path.home() / 'Library' / 'LaunchAgents' / (LABEL + '.plist')


def _launch_args():
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).resolve()), '--background']
    root = Path(__file__).resolve().parent
    # Same clean runtime the launcher uses (.venv_clean first, never Anaconda).
    py = None
    for env in ('runtime', '.venv_clean', '.venv'):
        exe = root / env / ('Scripts/pythonw.exe' if platform.system() == 'Windows' else 'bin/python')
        if exe.is_file():
            py = exe
            break
    if py is None:
        py = Path(sys.executable)
    return [str(py), str(root / 'main.py'), '--background']


def _linux_autostart():
    base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'autostart' / 'morphix.desktop'


def _linux_args():
    try:
        from linux_integration import launch_command
        return launch_command() + ['--background']
    except Exception:
        return _launch_args()


def is_enabled():
    system = platform.system()
    if system == 'Linux':
        return _linux_autostart().is_file()
    if system == 'Darwin':
        return _mac_plist().is_file()
    if system == 'Windows':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                winreg.QueryValueEx(key,'Morphix')
            return True
        except FileNotFoundError:
            return False
    return False


def set_enabled(enabled: bool):
    system = platform.system()
    if system == 'Darwin':
        plist = _mac_plist()
        if not enabled:
            if plist.is_file():
                plist.unlink()
            return
        plist.parent.mkdir(parents=True, exist_ok=True)
        log = Path.home() / 'Library' / 'Logs' / 'Morphix'
        log.mkdir(parents=True, exist_ok=True)
        payload = {
            'Label': LABEL,
            'ProgramArguments': _launch_args(),
            'RunAtLoad': True,
            'WorkingDirectory': str(Path(__file__).resolve().parent),
            'ProcessType': 'Interactive',
            'StandardOutPath': str(log/'autostart.log'),
            'StandardErrorPath': str(log/'autostart-error.log'),
        }
        temp = plist.with_suffix('.plist.tmp')
        temp.write_bytes(plistlib.dumps(payload))
        temp.replace(plist)
    elif system == 'Windows':
        import winreg
        path = r'Software\Microsoft\Windows\CurrentVersion\Run'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            if enabled:
                args = ' '.join('"'+arg+'"' for arg in _launch_args())
                winreg.SetValueEx(key,'Morphix',0,winreg.REG_SZ,args)
            else:
                try:
                    winreg.DeleteValue(key,'Morphix')
                except FileNotFoundError:
                    pass
    elif system == 'Linux':
        path = _linux_autostart()
        if not enabled:
            if path.is_file():
                path.unlink()
            return
        import shlex
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('[Desktop Entry]\nType=Application\nName=Morphix\n'
                        f"Exec={' '.join(shlex.quote(a) for a in _linux_args())}\n"
                        'Icon=morphix\nTerminal=false\nX-GNOME-Autostart-enabled=true\n'
                        'X-GNOME-Autostart-Delay=5\n', encoding='utf-8')
    elif enabled:
        raise RuntimeError('Launch at login is supported on macOS, Windows and Linux only.')
