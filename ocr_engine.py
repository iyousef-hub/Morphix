"""Offline Arabic/English OCR for PDFs via the native PyMuPDF OCR backend.

The traineddata files in assets/tessdata are redistributed under Apache-2.0.
OCR is enabled per-page where text is absent, preserving text on born-digital pages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _resource_roots():
    root = Path(__file__).resolve().parent
    yield root / 'assets' / 'tessdata'
    # PyInstaller --onedir, including macOS .app layouts
    if getattr(sys, '_MEIPASS', None):
        yield Path(sys._MEIPASS) / 'assets' / 'tessdata'
    if sys.platform == 'darwin':
        exe = Path(sys.executable).resolve()
        yield exe.parent.parent / 'Resources' / 'assets' / 'tessdata'
    for candidate in ('TESSDATA_PREFIX', 'MORPHIX_TESSDATA'):
        value = os.getenv(candidate)
        if value:
            yield Path(value)
    yield Path('/usr/share/tesseract-ocr/5/tessdata')


def find_tessdata():
    """Return a directory containing *both* eng and ara model files, or None."""
    for directory in _resource_roots():
        if all((directory / f'{lang}.traineddata').is_file() for lang in ('ara', 'eng')):
            return directory
    return None


def _ocr_page(page, *, language='ara+eng', dpi=220):
    tessdata = find_tessdata()
    if tessdata is None:
        raise RuntimeError('OCR language data missing (ara.traineddata and eng.traineddata). '
                           'Use the complete Morphix package, which includes both languages.')
    if not 120 <= dpi <= 400:
        raise ValueError('OCR DPI must be between 120 and 400')
    # PyMuPDF integrates its OCR engine: no external tesseract executable required.
    textpage = page.get_textpage_ocr(language=language, dpi=dpi,
                                      full=True, tessdata=str(tessdata))
    return page.get_text('text', textpage=textpage, sort=True).strip()


def extract_pdf_text(paths, out_dir, progress=None, *, force_ocr=False, dpi=220):
    """Export UTF-8 TXT with native text plus OCR for scanned pages.

    A partial scanned/native PDF is processed page-by-page, avoiding OCR on the
    pages that already have useful text. Optionally force OCR on all pages.
    No empty TXT is produced for unreadable inputs.
    """
    import pymupdf as fitz

    outputs = []
    output_folder = Path(out_dir)
    output_folder.mkdir(parents=True, exist_ok=True)
    from core_ops import unique_path

    for index, path in enumerate(paths, 1):
        pdf = Path(path)
        with fitz.open(pdf) as doc:
            if doc.needs_pass:
                raise ValueError(f'Password-protected PDF: {pdf.name}')
            if not doc.is_pdf:
                raise ValueError(f'Not a PDF: {pdf.name}')
            parts = []
            extracted = False
            for page_number, page in enumerate(doc, 1):
                text = page.get_text('text', sort=True).strip()
                if force_ocr or len(''.join(text.split())) < 8:
                    text = _ocr_page(page, dpi=dpi)
                if text:
                    extracted = True
                parts.append(f'===== Page {page_number} =====\n{text}')
            if not extracted:
                raise ValueError(f'No text recognized in {pdf.name}; the file may be blank or low resolution.')
            dest = unique_path(output_folder, f'{pdf.stem}_text.txt')
            dest.write_text('\n\n'.join(parts) + '\n', encoding='utf-8-sig')
            outputs.append(dest)
        if progress:
            progress(round(index * 100 / len(paths)))
    return outputs


def searchable_pdf(paths, out_dir, progress=None, *, dpi=200):
    """Build a searchable PDF; OCR image-only pages, preserve native PDF pages.

    Image-only pages are rasterized at a fixed DPI, then Tesseract embeds a
    transparent selectable text layer. Native text/vector pages are copied
    losslessly. This is not the same as editing OCR text in the original layout.
    """
    import pymupdf as fitz
    from core_ops import unique_path

    tessdata = find_tessdata()
    if tessdata is None:
        raise RuntimeError('OCR language data missing (ara.traineddata and eng.traineddata).')
    if not 120 <= dpi <= 400:
        raise ValueError('OCR DPI must be between 120 and 400')
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    outputs = []
    for i, path in enumerate(paths, 1):
        source = Path(path)
        with fitz.open(source) as original, fitz.open() as result:
            if original.needs_pass:
                raise ValueError(f'Password-protected PDF: {source.name}')
            if not original.is_pdf:
                raise ValueError(f'Not a PDF: {source.name}')
            for page_no, page in enumerate(original):
                native_text = page.get_text('text', sort=True).strip()
                if len(''.join(native_text.split())) >= 8:
                    result.insert_pdf(original, from_page=page_no, to_page=page_no)
                else:
                    pix = page.get_pixmap(dpi=dpi, alpha=False)
                    ocr_pdf = pix.pdfocr_tobytes(language='ara+eng', tessdata=str(tessdata))
                    with fitz.open('pdf', ocr_pdf) as ocr_document:
                        dest_page = result.new_page(width=page.rect.width, height=page.rect.height)
                        dest_page.show_pdf_page(dest_page.rect, ocr_document, 0)
            destination = unique_path(folder, f'{source.stem}_searchable.pdf')
            result.save(destination, deflate=True, garbage=3)
            outputs.append(destination)
        if progress:
            progress(round(i * 100 / len(paths)))
    return outputs


def extract_image_text(paths, out_dir, progress=None, *, dpi=220):
    """OCR images into UTF-8 text, for Arabic and English; no cloud upload.

    Ordinary mathematical symbols may be recognized, but equation layout and
    LaTeX reconstruction require a specialized math OCR model.
    """
    import pymupdf
    from PIL import Image, ImageOps
    from core_ops import unique_path
    from io import BytesIO

    output_folder = Path(out_dir)
    output_folder.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, source in enumerate(paths, 1):
        source = Path(source)
        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert('RGB')
            # Normalize unsupported formats (HEIC/WebP etc.) to PNG in memory.
            data = BytesIO()
            image.save(data, format='PNG')
            image_data = data.getvalue()
        with pymupdf.open() as doc:
            page = doc.new_page(width=image.width, height=image.height)
            page.insert_image(page.rect, stream=image_data)
            text = _ocr_page(page, dpi=dpi)
        if not text.strip():
            raise ValueError(f'No recognizable text in {source.name}')
        dest = unique_path(output_folder, source.stem + '_text.txt')
        dest.write_text(text + '\n', encoding='utf-8-sig')
        outputs.append(dest)
        if progress:
            progress(round(index * 100 / len(paths)))
    return outputs
