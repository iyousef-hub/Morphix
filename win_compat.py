"""Windows-only fixes applied once at start-up (no effect on macOS).

* Morphix is a windowed app, so every helper program it starts (FFmpeg,
  LibreOffice, the conversion worker…) would otherwise flash a black console
  window. Make CREATE_NO_WINDOW the default for every subprocess.
* Use UTF-8 for the console streams so Arabic file names never crash a print().
* Without a console, write messages to a log file.
"""
import sys


def apply():
    if sys.platform != 'win32':
        return
    import subprocess
    if getattr(subprocess.Popen, '_morphix_hidden', False):
        return
    CREATE_NO_WINDOW = 0x08000000
    original = subprocess.Popen.__init__

    def __init__(self, *args, **kwargs):
        if not kwargs.get('creationflags'):
            kwargs['creationflags'] = CREATE_NO_WINDOW
        original(self, *args, **kwargs)

    subprocess.Popen.__init__ = __init__
    subprocess.Popen._morphix_hidden = True
    # The windowed .exe has no console: keep its messages in a log file so
    # problems can be diagnosed (%LOCALAPPDATA%\Morphix\logs\morphix.log).
    if sys.stdout is None or sys.stderr is None:
        import os
        from pathlib import Path
        try:
            folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Morphix' / 'logs'
            folder.mkdir(parents=True, exist_ok=True)
            name = 'studio.log' if '--studio-window' in sys.argv else 'morphix.log'
            log = open(folder / name, 'a', encoding='utf-8', buffering=1)
            import time
            log.write(f"\n--- Morphix start {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(sys.argv[1:])} ---\n")
            if sys.stdout is None:
                sys.stdout = log
            if sys.stderr is None:
                sys.stderr = log
        except OSError:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


apply()
