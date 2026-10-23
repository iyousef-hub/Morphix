"""Keep Morphix in the user's explicitly selected project-local Python environment.

v1.4.8 always switched .venv_clean invocations back to .venv, causing the
macOS Studio to launch through an incompatible Anaconda Qt installation.
"""
import importlib.util
import os
import sys
from pathlib import Path

REQUIRED = {'PySide6': 'PySide6-Essentials', 'pymupdf': 'PyMuPDF',
            'PIL': 'Pillow', 'imageio_ffmpeg': 'imageio-ffmpeg'}


def missing_modules():
    return [label for module, label in REQUIRED.items()
            if importlib.util.find_spec(module) is None]


def project_venv_paths(root):
    root = Path(root).absolute()
    return [root / name for name in ('runtime', '.venv_clean', '.venv')]


def active_project_venv(root, prefix=None):
    prefix = Path(sys.prefix if prefix is None else prefix).absolute()
    return any(prefix == candidate for candidate in project_venv_paths(root))


def preferred_project_python(root):
    root = Path(root).absolute()
    for env_dir in project_venv_paths(root):
        exe = env_dir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if exe.is_file():
            return exe
    return None


def verify_or_relaunch(root):
    """Honor explicitly chosen .venv_clean/.venv; never switch between them."""
    root = Path(root).absolute()
    if not active_project_venv(root):
        selected = preferred_project_python(root)
        if selected is not None:
            print(f'[Morphix] Switching to project Python: {selected}', flush=True)
            os.execv(str(selected), [str(selected), str(root / 'main.py'), *sys.argv[1:]])
    missing = missing_modules()
    if missing:
        print('\n[Morphix] Runtime incomplete: ' + ', '.join(missing), flush=True)
        print('Install the dependencies in your active project environment:', flush=True)
        print('    python -m pip install -r requirements.txt', flush=True)
        raise SystemExit(2)
