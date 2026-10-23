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
            # Windows: soffice.exe hands the job to another process and can
            # return before the PDF exists; soffice.com waits and reports errors.
            console = candidate.with_suffix('.com')
            if sys.platform == 'win32' and candidate.suffix.lower() == '.exe' and console.is_file():
                return str(console)
            return str(candidate)
    return None


def _office_env():
    """Headless rendering. The 'svp' plugin exists on macOS/Linux only — on
    Windows forcing it makes LibreOffice quit silently without a PDF."""
    env = dict(os.environ)
    if sys.platform != 'win32':
        env['SAL_USE_VCLPLUGIN'] = 'svp'
    else:
        env.pop('SAL_USE_VCLPLUGIN', None)
    return env


def _profile_root():
    """A LibreOffice profile kept between conversions.

    Creating a fresh profile for every file made each conversion pay
    LibreOffice's whole first-start cost (very slow on Windows). The saved
    profile is reused; a lock keeps two conversions from sharing it at once
    (the second one then falls back to a temporary profile)."""
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'Morphix'
    elif os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Morphix'
    else:
        base = Path.home() / '.local' / 'share' / 'morphix'
    return base / 'office_profile'


class _ProfileLock:
    STALE_SECONDS = 20 * 60

    def __init__(self):
        self.root = _profile_root()
        self.lock = self.root.parent / 'office_profile.lock'
        self.owned = False

    def __enter__(self):
        import time
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            if self.lock.exists() and time.time() - self.lock.stat().st_mtime > self.STALE_SECONDS:
                self.lock.unlink()
            fd = os.open(str(self.lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            self.owned = True
            return self.root
        except OSError:
            return None

    def __exit__(self, *exc):
        if self.owned:
            try:
                self.lock.unlink()
            except OSError:
                pass


def _failure_details(done):
    details = ((done.stderr or '') + '\n' + (done.stdout or '')).strip()
    return details[-600:] if details else f'LibreOffice exit code {done.returncode}, no PDF was produced.'


def _try_ms_office(source, out_folder, export):
    """Windows + Microsoft Office installed: let Office export the PDF (much faster)."""
    if export != 'pdf':
        return None
    destination = None
    try:
        import ms_office
        if not ms_office.available(source.suffix):
            return None
        from core_ops import unique_path
        destination = unique_path(out_folder, f'{source.stem}.pdf')
        result = ms_office.to_pdf(source, destination)
        print(f'[Morphix] Converted with Microsoft Office: {source.name}', flush=True)
        return result
    except Exception as exc:
        print(f'[Morphix] Microsoft Office export failed, using LibreOffice: {exc}', flush=True)
        if destination is not None:
            try:
                Path(destination).unlink()
            except OSError:
                pass
        return None


def office_to_pdf(paths, out_dir, progress=None, *, timeout=300, export='pdf'):
    soffice = find_office_engine()
    if soffice is None and not (sys.platform == 'win32' and export == 'pdf'):
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
        done_by_office = _try_ms_office(source, out_folder, export)
        if done_by_office is not None:
            outputs.append(done_by_office)
            if progress:
                progress(round(index * 100 / len(paths)))
            continue
        if soffice is None:
            raise RuntimeError(_needs_libreoffice())
        with tempfile.TemporaryDirectory(prefix='morphix_office_') as root, _ProfileLock() as saved:
            root = Path(root)
            profile = (saved or (root / 'lo_profile')).as_uri()
            produced = root / 'out'
            produced.mkdir()
            # One input per invocation prevents output name collisions when several
            # selected files share a basename across different input directories.
            args = [soffice, f'-env:UserInstallation={profile}', '--headless', '--norestore',
                    '--convert-to', export, '--outdir', str(produced), str(source)]
            try:
                done = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, timeout=timeout, errors='replace', env=_office_env())
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f'Office conversion timed out: {source.name}') from exc
            files = list(produced.glob('*.pdf'))
            if done.returncode or len(files) != 1:
                raise RuntimeError(f'Office conversion failed for {source.name}: {_failure_details(done)}')
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
    with tempfile.TemporaryDirectory(prefix='morphix_office_') as root, _ProfileLock() as saved:
        root = Path(root)
        produced = root / 'out'
        produced.mkdir()
        args = [soffice, f'-env:UserInstallation={(saved or (root / "lo_profile")).as_uri()}', '--headless', '--norestore',
                '--convert-to', fmt, '--outdir', str(produced), str(source)]
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, errors='replace',
                              env=_office_env())
        files = list(produced.glob('*.' + fmt.split(':')[0]))
        if done.returncode or not files:
            raise RuntimeError(f'Conversion failed for {source.name}: {_failure_details(done)}')
        dest = Path(out_dir) / files[0].name
        shutil.move(str(files[0]), str(dest))
        return dest
