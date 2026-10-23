"""Standalone PDF/text/archive engine; callable and testable without Qt."""
from __future__ import annotations
import re
import shutil
import subprocess
import zipfile
import tarfile
from pathlib import Path


def unique_path(folder, name):
    dest = Path(folder) / name
    if not dest.exists(): return dest
    n = 2
    while (Path(folder) / f'{dest.stem}_{n}{dest.suffix}').exists(): n += 1
    return Path(folder) / f'{dest.stem}_{n}{dest.suffix}'


def _safe_base(name):
    return re.sub(r'[\\/\x00-\x1f]', '_', name)


def find_rar_writer():
    """Return a genuine licensed RAR writer, if available; never spoof .rar."""
    import os
    import sys
    bin_name = 'rar.exe' if sys.platform == 'win32' else 'rar'
    root = Path(__file__).resolve().parent
    candidates = [root / 'bin' / bin_name]
    if getattr(sys, '_MEIPASS', None):
        candidates.append(Path(sys._MEIPASS) / 'bin' / bin_name)
    if sys.platform == 'darwin':
        candidates.append(Path(sys.executable).resolve().parent.parent / 'Resources' / 'bin' / bin_name)
    if sys.platform == 'win32':
        candidates.append(Path(sys.executable).resolve().parent / 'bin' / bin_name)
    override = os.environ.get('MORPHIX_RAR')
    if override:
        candidates.append(Path(override))
    on_path = shutil.which('rar')
    if on_path:
        candidates.append(Path(on_path))
    return next((str(p) for p in candidates if p.is_file()), None)


def rar_writer_available():
    return bool(find_rar_writer())


def archive_files(paths, out_dir, fmt='zip', progress=None):
    """ZIP always supported. RAR requires a separately licensed/bundled rar writer."""
    fmt = fmt.lower()
    if fmt == 'rar':
        binary = find_rar_writer()
        if not binary:
            raise RuntimeError('RAR creation requires a separately licensed RAR writer. '
                               'The writer cannot legally be included without redistribution permission. '
                               'ZIP is fully supported without extra tools.')
        dest = unique_path(out_dir, 'Morphix_Files.rar')
        # Stage files with safe, distinct names; RAR otherwise silently collides
        # when two selected files from different directories share a basename.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='morphix_rar_') as staging:
            staged = []
            used = set()
            for source in paths:
                original = Path(source)
                if not original.is_file(): raise FileNotFoundError(original)
                base = _safe_base(original.name)
                name = base
                index = 2
                while name.lower() in used:
                    name = f'{Path(base).stem}_{index}{Path(base).suffix}'
                    index += 1
                used.add(name.lower())
                shutil.copy2(original, Path(staging) / name)
                staged.append(name)
            process = subprocess.run([binary, 'a', '-ep', '-idq', '-o-', str(dest), *staged],
                                     cwd=staging, capture_output=True, text=True, errors='replace')
            if process.returncode or not dest.is_file():
                dest.unlink(missing_ok=True)
                raise RuntimeError((process.stderr or process.stdout or 'RAR writer failed')[-800:])
        with dest.open('rb') as handle:
            if not handle.read(8).startswith((b'Rar!\x1a\x07\x00', b'Rar!\x1a\x07\x01\x00')):
                dest.unlink(missing_ok=True)
                raise RuntimeError('RAR writer did not create a genuine RAR archive')
        if progress is not None: progress(100)
        return [dest]
    if fmt in ('tar.gz', 'tgz'):
        dest = unique_path(out_dir, 'Morphix_Files.tar.gz')
        used = set()
        try:
            with tarfile.open(dest, 'w:gz') as archive:
                for i, original in enumerate(paths, 1):
                    source = Path(original)
                    if not source.is_file(): raise FileNotFoundError(source)
                    filename = _safe_base(source.name)
                    stem, suffix = Path(filename).stem, Path(filename).suffix
                    unique = filename
                    n = 2
                    while unique.lower() in used:
                        unique = f'{stem}_{n}{suffix}'
                        n += 1
                    used.add(unique.lower())
                    archive.add(source, arcname=unique, recursive=False)
                    if progress is not None: progress(round(i * 100 / len(paths)))
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return [dest]
    if fmt != 'zip': raise ValueError('Unsupported archive format')
    dest = unique_path(out_dir, 'Morphix_Files.zip')
    used = set()
    try:
        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
            for i, original in enumerate(paths, 1):
                p = Path(original)
                if not p.is_file(): raise FileNotFoundError(p)
                base = _safe_base(p.name)
                stem, suffix = Path(base).stem, Path(base).suffix
                candidate = base
                n = 2
                while candidate.lower() in used:
                    candidate = f'{stem}_{n}{suffix}'
                    n += 1
                used.add(candidate.lower())
                z.write(p, candidate)
                if progress is not None: progress(round(i * 100 / len(paths)))
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return [dest]


def extract_pdf_text(paths, out_dir, progress=None):
    """Compatibility entry point; now OCRs scanned Arabic/English pages automatically."""
    from ocr_engine import extract_pdf_text as extract_text_with_ocr
    return extract_text_with_ocr(paths, out_dir, progress)
