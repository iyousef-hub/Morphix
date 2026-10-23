"""Convert DOC/DOCX/PPT/PPTX/XLS/XLSX/ODT/ODS/ODP to PDF locally.

In packaged builds, prefer the LibreOffice runtime shipped *inside* Morphix.
In developer mode fall back to an explicitly configured or installed soffice.
Runs conversions in isolated temporary LibreOffice profiles.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OFFICE_EXTS = {'.doc', '.docx', '.ppt', '.pptx', '.pps', '.ppsx', '.xls', '.xlsx', '.xlsm', '.csv',
               '.odt', '.ods', '.odp', '.rtf'}


def _soffice_candidates():
    """Prioritize embedded engines and explicit override over system installs."""
    base = Path(__file__).resolve().parent
    yield base / 'office_runtime' / 'program' / 'soffice.exe'
    yield base / 'office_runtime' / 'program' / 'soffice'
    yield base / 'office_runtime' / 'LibreOffice.app' / 'Contents' / 'MacOS' / 'soffice'
    if getattr(sys, '_MEIPASS', None):
        root = Path(sys._MEIPASS)
        yield root / 'office_runtime' / 'program' / 'soffice.exe'
        yield root / 'office_runtime' / 'LibreOffice.app' / 'Contents' / 'MacOS' / 'soffice'
    exe = Path(sys.executable).resolve()
    if sys.platform == 'darwin':
        yield exe.parent.parent / 'Resources' / 'office_runtime' / 'LibreOffice.app' / 'Contents' / 'MacOS' / 'soffice'
    if sys.platform == 'win32':
        yield exe.parent / 'office_runtime' / 'program' / 'soffice.exe'
    env = os.getenv('MORPHIX_SOFFICE')
    if env:
        yield Path(env)
    if sys.platform == 'darwin':
        yield Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
    if sys.platform == 'win32':
        yield Path(os.getenv('PROGRAMFILES', r'C:\Program Files')) / 'LibreOffice' / 'program' / 'soffice.exe'
    for name in ('soffice', 'libreoffice'):
        candidate = shutil.which(name)
        if candidate:
            yield Path(candidate)


def find_office_engine():
    for candidate in _soffice_candidates():
        if candidate.is_file():
            return str(candidate)
    return None


def office_to_pdf(paths, out_dir, progress=None, *, timeout=300, export='pdf'):
    soffice = find_office_engine()
    if soffice is None:
        raise RuntimeError(_needs_libreoffice())
    from core_ops import unique_path
    out_folder = Path(out_dir)
    out_folder.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, path in enumerate(paths, 1):
        source = Path(path).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in OFFICE_EXTS:
            raise ValueError(f'Unsupported Office type: {source.name}')
        with tempfile.TemporaryDirectory(prefix='morphix_office_') as root:
            root = Path(root)
            profile = (root / 'lo_profile').as_uri()
            produced = root / 'out'
            produced.mkdir()
            # One input per invocation prevents output name collisions when several
            # selected files share a basename across different input directories.
            args = [soffice, f'-env:UserInstallation={profile}', '--headless',
                    '--convert-to', export, '--outdir', str(produced), str(source)]
            try:
                done = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, timeout=timeout, errors='replace',
                                      env={**os.environ, 'SAL_USE_VCLPLUGIN': 'svp'})
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f'Office conversion timed out: {source.name}') from exc
            files = list(produced.glob('*.pdf'))
            if done.returncode or len(files) != 1:
                details = (done.stderr or done.stdout).strip()
                raise RuntimeError(f'Office conversion failed for {source.name}: {details[-600:]}')
            destination = unique_path(out_folder, f'{source.stem}.pdf')
            shutil.move(str(files[0]), str(destination))
            outputs.append(destination)
        if progress:
            progress(round(index * 100 / len(paths)))
    return outputs


def _needs_libreoffice():
    try:
        from i18n import tr
        return tr('Converting Office files needs LibreOffice (free). Install it from libreoffice.org, '
                  'then try again.')
    except Exception:
        return 'Converting Office files needs LibreOffice (free). Install it from libreoffice.org, then try again.'


def office_convert(source, out_dir, fmt, *, timeout=300):
    """Convert one file to another office format (e.g. .xls → .xlsx)."""
    soffice = find_office_engine()
    if soffice is None:
        raise RuntimeError(_needs_libreoffice())
    source = Path(source).resolve()
    with tempfile.TemporaryDirectory(prefix='morphix_office_') as root:
        root = Path(root)
        produced = root / 'out'
        produced.mkdir()
        args = [soffice, f'-env:UserInstallation={(root / "lo_profile").as_uri()}', '--headless',
                '--convert-to', fmt, '--outdir', str(produced), str(source)]
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, errors='replace',
                              env={**os.environ, 'SAL_USE_VCLPLUGIN': 'svp'})
        files = list(produced.glob('*.' + fmt.split(':')[0]))
        if done.returncode or not files:
            raise RuntimeError(f'Conversion failed for {source.name}: {(done.stderr or done.stdout)[-600:]}')
        dest = Path(out_dir) / files[0].name
        shutil.move(str(files[0]), str(dest))
        return dest
