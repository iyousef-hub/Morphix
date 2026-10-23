"""Merge PDF pages and raster image pages into one PDF in exactly the given order.

This module is independent of Qt: it runs in Morphix's isolated conversion worker.
"""
from io import BytesIO
from pathlib import Path


def merge_documents(paths, progress=None):
    """Return an open PyMuPDF document; caller MUST close it.

    Each PDF contributes all pages, each raster image contributes exactly one
    page. Paths are intentionally not sorted or deduplicated by this routine.
    """
    import pymupdf as fitz
    from PIL import Image, ImageOps
    from file_intelligence import category_for

    if not paths:
        raise ValueError('Choose at least one file to merge.')
    result = fitz.open()
    try:
        for index, path in enumerate(paths, 1):
            path = Path(path)
            if not path.is_file():
                raise FileNotFoundError(f'File not found: {path}')
            kind = category_for(path)
            if kind == 'pdf':
                with fitz.open(path) as source:
                    if source.needs_pass:
                        raise ValueError(f'Protected PDF requires a password: {path.name}')
                    if source.page_count == 0:
                        raise ValueError(f'The PDF has no pages: {path.name}')
                    result.insert_pdf(source, from_page=0, to_page=source.page_count - 1)
            elif kind == 'image':
                # Apply EXIF orientation so portrait phone images remain upright.
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(source)
                    image.load()
                    width, height = image.size
                    if width <= 0 or height <= 0:
                        raise ValueError(f'Invalid image dimensions: {path.name}')
                    buf = BytesIO()
                    if image.mode in ('RGBA', 'LA') or ('transparency' in image.info):
                        image.convert('RGBA').save(buf, format='PNG')
                    else:
                        image.convert('RGB').save(buf, format='JPEG', quality=94)
                    page = result.new_page(width=width, height=height)
                    page.insert_image(page.rect, stream=buf.getvalue(), keep_proportion=True)
            else:
                raise ValueError(f'PDF merge supports only PDF and images: {path.name}')
            if progress is not None:
                progress.emit(round(index / len(paths) * 100))
        if result.page_count < 1:
            raise ValueError('No pages to merge.')
        return result
    except BaseException:
        result.close()
        raise
