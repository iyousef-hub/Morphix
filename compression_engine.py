"""Local compression controls shared by Morphix's wheel and Studio.

All routines create NEW output files. The inputs are never overwritten.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def image_quality(strength: int) -> int:
    """Strength 0=best visual quality, 100=smallest JPEG (usually)."""
    strength = max(0, min(100, int(strength)))
    return max(20, min(95, round(95 - 0.73 * strength)))


RASTER_FROM = 86   # strength at which pages are re-drawn as compressed images


def pdf_rewrite_params(strength: int) -> dict | None:
    """Return lossier embedded-image settings; low strength preserves images."""
    strength = max(0, min(100, int(strength)))
    if strength < 30:
        return None
    return {
        'dpi_threshold': max(100, round(350 - strength * 2.3)),
        'dpi_target': max(60, round(245 - strength * 1.95)),
        'quality': image_quality(strength),
    }


def raster_params(strength: int) -> dict | None:
    """Extreme levels: every page becomes one JPEG (text is no longer selectable)."""
    strength = max(0, min(100, int(strength)))
    if strength < RASTER_FROM:
        return None
    t = (strength - RASTER_FROM) / (100 - RASTER_FROM)
    return {'dpi': round(110 - 55 * t), 'quality': round(50 - 26 * t)}


def _rasterize_pdf(source_path, dest_path, *, dpi, quality, grayscale=False):
    import pymupdf as fitz
    from io import BytesIO
    from PIL import Image
    with fitz.open(source_path) as src, fitz.open() as out:
        for page in src:
            pix = page.get_pixmap(dpi=dpi, alpha=False,
                                  colorspace=fitz.csGRAY if grayscale else fitz.csRGB)
            mode = 'L' if grayscale else 'RGB'
            with Image.frombytes(mode, (pix.width, pix.height), pix.samples) as im:
                buf = BytesIO()
                im.save(buf, format='JPEG', quality=quality, optimize=True, progressive=True)
            new = out.new_page(width=page.rect.width, height=page.rect.height)
            new.insert_image(new.rect, stream=buf.getvalue())
        out.save(str(dest_path), garbage=4, deflate=True, clean=True)


def flatten_for_jpeg(image):
    """Composite transparent pixels on white (not black), preserving dimensions."""
    from PIL import Image
    if image.mode == 'RGB':
        return image.copy()
    rgba = image.convert('RGBA')
    bg = Image.new('RGB', rgba.size, 'white')
    bg.paste(rgba, mask=rgba.getchannel('A'))
    return bg


def save_image_compressed(image, output: str | Path, *, quality: int = 72, resize_max: int | None = None):
    """Compress an already EXIF-normalized PIL Image as JPEG."""
    from PIL import Image
    quality = max(10, min(95, int(quality)))
    im = flatten_for_jpeg(image)
    if resize_max is not None:
        resize_max = int(resize_max)
        if resize_max < 64:
            raise ValueError('Maximum dimension must be at least 64 pixels.')
        im.thumbnail((resize_max, resize_max), Image.Resampling.LANCZOS)
    im.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)


def save_pdf_compressed(document, destination: str | Path, *, strength: int = 50, grayscale: bool = False):
    """Save the SMALLEST valid candidate for the requested strength.

    < 30   structural optimisation only (lossless)
    30-85  plus image down-sampling / JPEG re-compression (text stays selectable)
    86-100 plus "pages as images": each page is re-drawn as a JPEG at 110→55 DPI.
           Always shrinks scanned and image-heavy PDFs a lot; text becomes part
           of the picture (use OCR afterwards to make it searchable again).
    The original file is never modified, and the result is never larger than
    the structurally optimised copy.
    """
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.morphix_pdf_', dir=dest.parent) as tmp:
        try:
            document.subset_fonts()          # drop unused glyphs (lossless)
        except Exception:
            pass
        baseline = Path(tmp) / 'baseline.pdf'
        document.save(str(baseline), garbage=4, deflate=True, clean=True,
                      deflate_images=True, deflate_fonts=True)
        candidates = [baseline]
        params = pdf_rewrite_params(strength)
        if params and callable(getattr(document, 'rewrite_images', None)):
            try:
                if grayscale:
                    params = dict(params, set_to_gray=True)
                document.rewrite_images(**params)
                rewrite = Path(tmp) / 'recompressed.pdf'
                document.save(str(rewrite), garbage=4, deflate=True, clean=True)
                # Some PyMuPDF versions can discard transparent PNG images
                # during rewrite_images() without raising an exception.
                import pymupdf as fitz
                with fitz.open(baseline) as before, fitz.open(rewrite) as after:
                    retained = (before.page_count == after.page_count and all(
                        len(after[i].get_image_info()) >= len(before[i].get_image_info())
                        for i in range(before.page_count)))
                if retained:
                    candidates.append(rewrite)
            except (RuntimeError, ValueError, TypeError):
                pass
        raster = raster_params(strength)
        if raster:
            try:
                flat = Path(tmp) / 'raster.pdf'
                _rasterize_pdf(baseline, flat, grayscale=grayscale, **raster)
                candidates.append(flat)
            except Exception:
                pass
        best = min(candidates, key=lambda p: p.stat().st_size)
        os.replace(best, dest)
    return dest
