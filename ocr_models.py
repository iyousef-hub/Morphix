"""Optional, more accurate OCR engines (downloaded from the Add-ons page).

Engines
-------
standard  Tesseract (built in) — light, fast, makes searchable PDFs.
accurate  PaddleOCR PP-OCR models via RapidOCR / ONNX Runtime:
          English & Latin model built in (PP-OCRv6), Arabic model downloaded (PP-OCRv5).
formula   Formula image → LaTeX (RapidLaTeXOCR / pix2tex, ONNX), downloaded.
"""
from __future__ import annotations

import hashlib
import os
import re
import urllib.request
from pathlib import Path

ARABIC_REC = {
    'file': 'arabic_PP-OCRv5_rec_mobile.onnx',
    'size': '≈ 8 MB',
    'sha256': 'c1192e632d0baa9146ae5b756a0e635e3dc63c1733737ebfd1629e87144e9295',
    'urls': ['https://github.com/iyousef-hub/Morphix/releases/download/addons-models/arabic_PP-OCRv5_rec_mobile.onnx',
             'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv5/rec/'
             'arabic_PP-OCRv5_rec_mobile.onnx'],
}
FORMULA = {
    'size': '≈ 170 MB',
    'base': 'https://github.com/RapidAI/RapidLaTeXOCR/releases/download/v0.0.0/',
    'files': ('image_resizer.onnx', 'encoder.onnx', 'decoder.onnx', 'tokenizer.json'),
}


def models_root() -> Path:
    from transcription_engine import models_root as root
    return root() / 'ocr'


def arabic_model():
    path = models_root() / ARABIC_REC['file']
    return path if path.is_file() and path.stat().st_size > 1_000_000 else None


def formula_dir():
    folder = models_root() / 'formula'
    return folder if all((folder / f).is_file() for f in FORMULA['files']) else None


def accurate_available():
    # Only look for the package: importing it would load ONNX Runtime and OpenCV
    # into the interface process (the OCR itself runs in the worker process).
    import importlib.util
    try:
        return importlib.util.find_spec('rapidocr') is not None
    except Exception:
        return False


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _fetch(url, dest, progress=None, base=0, span=100):
    tmp = Path(str(dest) + '.part')
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, 'wb') as out:
        total = int(resp.headers.get('Content-Length') or 0)
        done = 0
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            out.write(block)
            done += len(block)
            if progress and total:
                progress(min(99, base + done * span // total))
    os.replace(tmp, dest)


def download(kind, progress=None, status=None):
    folder = models_root()
    folder.mkdir(parents=True, exist_ok=True)
    if kind == 'ocr_arabic':
        dest = folder / ARABIC_REC['file']
        errors = []
        for url in ARABIC_REC['urls']:
            try:
                if status:
                    status('Downloading the Arabic OCR model (≈ 8 MB) — one time only…')
                _fetch(url, dest, progress)
                if _sha256(dest) != ARABIC_REC['sha256']:
                    dest.unlink(missing_ok=True)
                    raise RuntimeError('checksum mismatch')
                break
            except Exception as exc:
                errors.append(f'{url.split("/")[2]}: {exc}')
        else:
            raise RuntimeError('The model could not be downloaded. Please check your internet connection '
                               'and try again.\n' + '\n'.join(errors))
        if progress:
            progress(100)
        return dest
    if kind == 'ocr_formula':
        target = folder / 'formula'
        target.mkdir(parents=True, exist_ok=True)
        files = FORMULA['files']
        if status:
            status('Downloading the formula model (≈ 170 MB) — one time only…')
        for i, name in enumerate(files):
            dest = target / name
            if dest.is_file() and dest.stat().st_size > 1000:
                continue
            try:
                _fetch(FORMULA['base'] + name, dest, progress, i * 100 // len(files), 100 // len(files))
            except Exception as exc:
                raise RuntimeError('The model could not be downloaded. Please check your internet connection '
                                   f'and try again.\n{exc}') from exc
        if progress:
            progress(100)
        return target
    raise ValueError(kind)


# --------------------------------------------------------------------- accurate OCR
_ENGINES = {}
_AR = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')


def _engine(lang):
    """lang: 'ar' (Arabic + Latin) or 'latin'."""
    if lang in _ENGINES:
        return _ENGINES[lang]
    import logging
    from rapidocr import RapidOCR
    params = {'Global.log_level': 'error'}
    if lang == 'ar':
        from rapidocr import LangRec, OCRVersion, ModelType
        model = arabic_model()
        if model is None:
            raise RuntimeError('The Arabic OCR model is not downloaded yet. Open Add-ons → Accurate OCR · Arabic.')
        params.update({'Rec.model_path': str(model), 'Rec.lang_type': LangRec.ARABIC,
                       'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE})
    engine = RapidOCR(params=params)
    logging.getLogger('RapidOCR').setLevel(logging.ERROR)
    _ENGINES[lang] = engine
    return engine


def _lines_from(result):
    """Group recognised boxes into lines (top → bottom), right-to-left for Arabic lines."""
    if result is None or result.boxes is None or not len(result.txts):
        return []
    items = []
    for box, text in zip(result.boxes, result.txts):
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append({'y0': min(ys), 'y1': max(ys), 'x': min(xs), 'text': text.strip()})
    items.sort(key=lambda i: (i['y0'] + i['y1']) / 2)
    lines = []
    for it in items:
        if not it['text']:
            continue
        mid = (it['y0'] + it['y1']) / 2
        if lines and abs(mid - lines[-1]['mid']) < 0.5 * (it['y1'] - it['y0']):
            lines[-1]['items'].append(it)
        else:
            lines.append({'mid': mid, 'items': [it]})
    out = []
    for line in lines:
        text = ' '.join(i['text'] for i in line['items'])
        rtl = len(_AR.findall(text)) > len(re.findall('[A-Za-z]', text))
        line['items'].sort(key=lambda i: -i['x'] if rtl else i['x'])
        out.append(' '.join(i['text'] for i in line['items']))
    return out


def accurate_text(paths, out_dir, progress=None, *, lang='auto', status=None):
    """Images and PDFs → UTF-8 .txt with the PaddleOCR models."""
    import numpy as np
    from PIL import Image, ImageOps
    from core_ops import unique_path
    from tools_engine import register_heic
    register_heic()
    if lang == 'auto':
        lang = 'ar' if arabic_model() else 'latin'
    engine = _engine('ar' if lang == 'ar' else 'latin')
    outputs = []
    for i, src in enumerate(paths):
        src = Path(src)
        pages = []
        if src.suffix.lower() == '.pdf':
            import pymupdf as fitz
            with fitz.open(src) as doc:
                for n, page in enumerate(doc, 1):
                    if status:
                        status(f'{src.name} · page {n}/{len(doc)}')
                    native = page.get_text('text').strip()
                    if len(native) > 40:
                        pages.append(native)
                        continue
                    pix = page.get_pixmap(dpi=220, alpha=False)
                    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3]
                    pages.append('\n'.join(_lines_from(engine(arr[..., ::-1].copy()))))
                    if progress:
                        progress(min(99, round((i + n / len(doc)) * 100 / len(paths))))
        else:
            with Image.open(src) as original:
                rgb = np.asarray(ImageOps.exif_transpose(original).convert('RGB'))[..., ::-1].copy()
            pages.append('\n'.join(_lines_from(engine(rgb))))
        text = '\n\n'.join(p for p in pages if p.strip())
        if not text.strip():
            raise ValueError(f'No recognizable text in {src.name}')
        dest = unique_path(out_dir, src.stem + '_text.txt')
        dest.write_text(text + '\n', encoding='utf-8-sig')
        outputs.append(dest)
        if progress:
            progress(round((i + 1) * 100 / len(paths)))
    return outputs


# --------------------------------------------------------------------- formulas
def formulas_to_latex(paths, out_dir, progress=None, status=None):
    """Each image (one formula per image) → LaTeX. Writes a Markdown file with $$…$$ blocks."""
    from PIL import Image, ImageOps
    from core_ops import unique_path
    from latex_ocr import LatexOCR
    from tools_engine import register_heic
    register_heic()
    folder = formula_dir()
    if folder is None:
        raise RuntimeError('The formula model is not downloaded yet. Open Add-ons → Formulas → LaTeX.')
    if status:
        status('Loading the formula model…')
    model = LatexOCR(folder)
    results = []
    for i, src in enumerate(paths, 1):
        src = Path(src)
        with Image.open(src) as original:
            image = ImageOps.exif_transpose(original).convert('RGB')
        results.append((src.name, model(image)))
        if progress:
            progress(round(i * 95 / len(paths)))
    name = (Path(paths[0]).stem + '_formula.md') if len(paths) == 1 else 'formulas.md'
    dest = unique_path(out_dir, name)
    blocks = [f'<!-- {n} -->\n$$\n{latex}\n$$\n' for n, latex in results]
    dest.write_text('\n'.join(blocks), encoding='utf-8')
    tex = unique_path(out_dir, dest.stem + '.tex')
    tex.write_text('\n\n'.join(f'% {n}\n\\[\n{latex}\n\\]' for n, latex in results) + '\n', encoding='utf-8')
    if progress:
        progress(100)
    return [dest, tex]
