"""Document scanner (Morphix 1.10): photos of paper → clean, flat pages → PDF.

Headless; used by the scanner window (previews) and the worker (full quality).

* find_document()  — finds the sheet's four corners in a photo
* flatten()        — straightens the sheet (perspective correction)
* apply_filter()   — Original · Enhanced · Grayscale · Black & white, with shadow removal
* build_scan()     — the finished PDF (A4 / Letter / original size, optional searchable
                     Arabic + English text, ID-card layout) or one image per page
"""
from __future__ import annotations

import io
from pathlib import Path

FILTERS = ('original', 'enhanced', 'gray', 'bw')
PAGE_SIZES = {'a4': (595.28, 841.89), 'letter': (612.0, 792.0)}
# quality → (longest side in pixels, JPEG quality)
QUALITY = {'high': (3300, 90), 'balanced': (2400, 80), 'small': (1700, 66)}
ID_CARD_MM = (85.6, 53.98)
MM = 72 / 25.4


# --------------------------------------------------------------------- loading
def load_rgb(path, max_side=None):
    """Photo as an RGB numpy array, turned upright by its EXIF tag (HEIC works too)."""
    import numpy as np
    from PIL import Image, ImageOps
    try:
        import tools_engine
        tools_engine.register_heic()
    except Exception:
        pass
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            back = Image.new('RGB', im.size, 'white')
            back.paste(im, mask=im.split()[-1])
            im = back
        else:
            im = im.convert('RGB')
        if max_side and max(im.size) > max_side:
            im.thumbnail((max_side, max_side), Image.LANCZOS)
        return np.asarray(im).copy()


# --------------------------------------------------------------------- corners
def _order(pts):
    """Corners as top-left, top-right, bottom-right, bottom-left."""
    import numpy as np
    pts = np.asarray(pts, dtype='float32').reshape(4, 2)
    s = pts.sum(1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], dtype='float32')


def _quad_ok(quad, w, h, min_area=0.18):
    import cv2
    import numpy as np
    q = _order(quad)
    if not cv2.isContourConvex(q.astype('int32').reshape(-1, 1, 2)):
        return False
    area = cv2.contourArea(q)
    if area < min_area * w * h:
        return False
    # reject slivers: every side at least 15 % of the image's shorter side
    sides = [np.linalg.norm(q[i] - q[(i + 1) % 4]) for i in range(4)]
    return min(sides) > 0.15 * min(w, h)


def _candidates(gray):
    """Edge maps that tend to show a sheet's outline in different lighting."""
    import cv2
    import numpy as np
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    med = float(np.median(blur))
    for lo, hi in ((0.66 * med, 1.33 * med), (30, 120), (60, 180)):
        edges = cv2.Canny(blur, max(5, lo), max(lo + 10, hi))
        yield cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=2)
    # a bright sheet on a darker surface
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield cv2.morphologyEx(th, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))


def find_document(rgb):
    """Return (corners, found). Corners are 4 [x, y] pairs from 0 to 1 (TL, TR, BR, BL).

    When no sheet stands out, the whole picture is used (found = False).
    """
    import cv2
    import numpy as np
    h0, w0 = rgb.shape[:2]
    scale = 900.0 / max(h0, w0)
    small = cv2.resize(rgb, (max(1, int(w0 * scale)), max(1, int(h0 * scale))), interpolation=cv2.INTER_AREA) \
        if scale < 1 else rgb
    h, w = small.shape[:2]
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    best, best_area = None, 0
    for edges in _candidates(gray):
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:6]:
            if cv2.contourArea(c) < 0.18 * w * h:
                break
            hull = cv2.convexHull(c)
            peri = cv2.arcLength(hull, True)
            quad = None
            for eps in (0.015, 0.02, 0.03, 0.045, 0.06):
                approx = cv2.approxPolyDP(hull, eps * peri, True)
                if len(approx) == 4:
                    quad = approx.reshape(4, 2)
                    break
            if quad is None:
                quad = cv2.boxPoints(cv2.minAreaRect(hull))
            # a contour that is just the picture frame is not a sheet
            q = _order(quad)
            margin = 0.012 * max(w, h)
            touching = sum(1 for x, y in q if x < margin or y < margin or x > w - margin or y > h - margin)
            if touching >= 3:
                continue
            if _quad_ok(q, w, h):
                area = cv2.contourArea(q)
                if area > best_area:
                    best, best_area = q, area
        if best is not None:
            break
    if best is None:
        return full_corners(), False
    norm = [[float(x) / w, float(y) / h] for x, y in _order(best)]
    return [[min(1.0, max(0.0, x)), min(1.0, max(0.0, y))] for x, y in norm], True


def full_corners():
    return [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


# --------------------------------------------------------------------- flatten
def flatten(rgb, corners, max_side=None):
    """Straighten the sheet inside the four corners (normalized) into a flat page."""
    import cv2
    import numpy as np
    h, w = rgb.shape[:2]
    q = _order([[x * (w - 1), y * (h - 1)] for x, y in corners])
    if np.allclose(q, _order([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]), atol=1.5):
        out = rgb
    else:
        width = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3]))
        height = max(np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1]))
        ratio = _true_ratio(q, w, h)            # the sheet's real width ÷ height
        if ratio:
            if width / height > ratio:
                width = height * ratio
            else:
                height = width / ratio
        width, height = max(int(round(width)), 16), max(int(round(height)), 16)
        dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype='float32')
        m = cv2.getPerspectiveTransform(q, dst)
        out = cv2.warpPerspective(rgb, m, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        # a hair inside the edge: no strip of table or shadow along the borders
        ix, iy = max(1, int(width * 0.006)), max(1, int(height * 0.006))
        out = _trim_dark_edges(out[iy:height - iy, ix:width - ix])
    if max_side and max(out.shape[:2]) > max_side:
        s = max_side / max(out.shape[:2])
        out = cv2.resize(out, (max(1, int(out.shape[1] * s)), max(1, int(out.shape[0] * s))),
                         interpolation=cv2.INTER_AREA)
    return out


def _trim_dark_edges(rgb, limit=0.035):
    """Cut off thin dark strips (table, shadow) left along the sheet's edges."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype('float32')
    h, w = gray.shape
    paper = float(np.percentile(gray, 75))
    if paper < 60:
        return rgb

    def first_clean(lines, n):
        for i in range(n):
            if lines(i) > 0.8 * paper:
                return i
        return 0

    my, mx = max(1, int(h * limit)), max(1, int(w * limit))
    top = first_clean(lambda i: np.median(gray[i, :]), my)
    bottom = first_clean(lambda i: np.median(gray[h - 1 - i, :]), my)
    left = first_clean(lambda i: np.median(gray[:, i]), mx)
    right = first_clean(lambda i: np.median(gray[:, w - 1 - i]), mx)
    if top or bottom or left or right:
        pad_y, pad_x = max(1, int(h * 0.002)), max(1, int(w * 0.002))
        t = top + pad_y if top else 0
        b = h - (bottom + pad_y if bottom else 0)
        l = left + pad_x if left else 0
        r = w - (right + pad_x if right else 0)
        return rgb[t:b, l:r]
    return rgb


def _true_ratio(q, w, h):
    """Real width ÷ height of the photographed rectangle, undoing the camera's perspective.

    Zhang & He, "Whiteboard scanning and image enhancement" (2007): from the four corners the
    camera's focal length is estimated, then the rectangle's true proportions. Common paper
    sizes (A-series, Letter) are snapped to when within 3 %.
    """
    import numpy as np
    u0, v0 = w / 2.0, h / 2.0
    tl, tr, br, bl = [np.array([x, y, 1.0]) for x, y in q]
    m1, m2, m3, m4 = tl, tr, bl, br
    try:
        k2 = np.dot(np.cross(m1, m4), m3) / np.dot(np.cross(m2, m4), m3)
        k3 = np.dot(np.cross(m1, m4), m2) / np.dot(np.cross(m3, m4), m2)
        n2 = k2 * m2 - m1
        n3 = k3 * m3 - m1
        ratio = None
        if abs(n2[2]) > 1e-9 and abs(n3[2]) > 1e-9:
            f2 = -((n2[0] * n3[0] - (n2[0] * n3[2] + n2[2] * n3[0]) * u0 + n2[2] * n3[2] * u0 * u0) +
                   (n2[1] * n3[1] - (n2[1] * n3[2] + n2[2] * n3[1]) * v0 + n2[2] * n3[2] * v0 * v0)) / (n2[2] * n3[2])
            if f2 > 0:
                f = np.sqrt(f2)
                a = np.array([[f, 0, u0], [0, f, v0], [0, 0, 1.0]])
                ai = np.linalg.inv(a)
                b = ai.T @ ai
                ratio = np.sqrt((n2 @ b @ n2) / (n3 @ b @ n3))
        if ratio is None or not np.isfinite(ratio):
            ratio = np.sqrt((n2[0] ** 2 + n2[1] ** 2) / (n3[0] ** 2 + n3[1] ** 2))
    except (ZeroDivisionError, FloatingPointError, np.linalg.LinAlgError):
        return None
    if not np.isfinite(ratio) or not 0.2 < ratio < 5:
        return None
    for paper in (1 / np.sqrt(2), 8.5 / 11, 85.6 / 53.98):
        for r in (paper, 1 / paper):
            if abs(ratio / r - 1) < 0.03:
                return float(r)
    return float(ratio)


def rotate(rgb, degrees):
    import numpy as np
    k = (int(degrees) // 90) % 4
    return np.ascontiguousarray(np.rot90(rgb, -k)) if k else rgb


# --------------------------------------------------------------------- filters
def _background(channel):
    """Smooth estimate of the paper (light and shadows) without the ink."""
    import cv2
    h, w = channel.shape[:2]
    k = max(3, (int(min(h, w) / 24) | 1))
    small = cv2.resize(channel, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_AREA)
    ks = max(3, (k // 4) | 1)
    bg = cv2.morphologyEx(small, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks)))
    bg = cv2.medianBlur(bg, ks if ks <= 255 else 255)
    return cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)


def _flatten_light(channel):
    """Divide out the background: shadows and uneven light disappear, paper turns white."""
    import cv2
    import numpy as np
    bg = _background(channel).astype('float32')
    out = channel.astype('float32') / np.maximum(bg, 1.0) * 255.0
    return np.clip(out, 0, 255).astype('uint8')


def _stretch(channel, low=1.0, high=99.5):
    import numpy as np
    lo, hi = np.percentile(channel, (low, high))
    if hi - lo < 10:
        return channel
    out = (channel.astype('float32') - lo) * (255.0 / (hi - lo))
    return np.clip(out, 0, 255).astype('uint8')


def apply_filter(rgb, name):
    """Return the page with the chosen look. Black & white comes back as a 2-D array."""
    import cv2
    import numpy as np
    if name == 'original' or name not in FILTERS:
        return rgb
    if name == 'enhanced':
        planes = [_flatten_light(rgb[:, :, i]) for i in range(3)]
        out = cv2.merge(planes)
        out = np.dstack([_stretch(out[:, :, i], 0.5, 99.0) for i in range(3)])
        hsv = cv2.cvtColor(out, cv2.COLOR_RGB2HSV).astype('float32')
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
        out = cv2.cvtColor(hsv.astype('uint8'), cv2.COLOR_HSV2RGB)
        # gentle sharpening for crisp text
        blur = cv2.GaussianBlur(out, (0, 0), 1.2)
        return cv2.addWeighted(out, 1.35, blur, -0.35, 0)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    flat = _flatten_light(gray)
    if name == 'gray':
        out = _stretch(flat, 0.5, 98.5)
        blur = cv2.GaussianBlur(out, (0, 0), 1.0)
        return cv2.addWeighted(out, 1.3, blur, -0.3, 0)
    # black & white: adaptive threshold on the evened-out page
    h, w = flat.shape
    block = max(15, (int(min(h, w) / 40) | 1))
    den = cv2.medianBlur(flat, 3)
    bw = cv2.adaptiveThreshold(den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 12)
    # drop isolated specks
    inv = 255 - bw
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, 8)
    tiny = max(2, int(h * w / 2_000_000))
    mask = np.isin(labels, np.where(stats[:, cv2.CC_STAT_AREA] <= tiny)[0])
    mask[labels == 0] = False
    bw[mask] = 255
    return bw


def process_page(path, page, max_side=None, preview=False):
    """One page (dict: path, corners, rotation, filter) → finished numpy image."""
    rgb = load_rgb(path, max_side=1600 if preview else None)
    flat = flatten(rgb, page.get('corners') or full_corners(), max_side=max_side)
    flat = rotate(flat, page.get('rotation', 0))
    return apply_filter(flat, page.get('filter', 'enhanced'))


# --------------------------------------------------------------------- output
def _encode(img, quality):
    """Encode for the PDF: 1-bit PNG for black & white (tiny and sharp), JPEG otherwise."""
    from PIL import Image
    buf = io.BytesIO()
    if img.ndim == 2 and set(map(int, __import__('numpy').unique(img[::7, ::7]))) <= {0, 255}:
        Image.fromarray(img).convert('1').save(buf, 'PNG', optimize=True)
        return buf.getvalue(), 'png'
    Image.fromarray(img).save(buf, 'JPEG', quality=quality, optimize=True, progressive=True, subsampling=0
                              if quality >= 88 else 2)
    return buf.getvalue(), 'jpg'


def _page_rect(size_key, w, h):
    """Page size in points for an image of w×h pixels."""
    if size_key in PAGE_SIZES:
        pw, ph = PAGE_SIZES[size_key]
        return (ph, pw) if w > h * 1.08 else (pw, ph)
    # original: keep the photo's proportions on a page as wide as A4
    pw = PAGE_SIZES['a4'][0] if w <= h else PAGE_SIZES['a4'][1]
    return pw, pw * h / w


def _ocr_overlay(doc_page, img, rect):
    """Add invisible Arabic + English text over the picture so the PDF can be searched."""
    import pymupdf as fitz
    from ocr_engine import find_tessdata
    from PIL import Image
    tess = find_tessdata()
    if tess is None:
        raise RuntimeError('OCR language data missing (ara.traineddata and eng.traineddata).')
    pil = Image.fromarray(img).convert('RGB')
    if max(pil.size) > 3000:
        pil.thumbnail((3000, 3000))
    buf = io.BytesIO(); pil.save(buf, 'PNG')
    pix = fitz.Pixmap(buf.getvalue())
    with fitz.open('pdf', pix.pdfocr_tobytes(language='ara+eng', tessdata=str(tess))) as ocr:
        src = ocr[0]
        for xref, *_ in src.get_images(full=True):
            try:
                src.delete_image(xref)          # keep only the invisible text layer
            except Exception:
                pass
        doc_page.show_pdf_page(rect, ocr, 0, overlay=True)


def build_scan(pages, out_dir, progress=None, *, name='Scan', page_size='a4', quality='balanced',
               ocr=False, id_card=False, output='pdf', status=None):
    """Turn the pages into one PDF (or images). Returns the files written."""
    import pymupdf as fitz
    from core_ops import unique_path
    if not pages:
        raise ValueError('There are no pages to scan.')
    max_side, jpeg_q = QUALITY.get(quality, QUALITY['balanced'])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = ''.join(c for c in str(name) if c not in '\\/:*?"<>|').strip() or 'Scan'
    n = len(pages)

    def tick(i, label=None):
        if progress:
            progress(round(i * 100 / max(n, 1)))
        if status and label:
            status(label)

    if output == 'images':
        from PIL import Image
        outs = []
        for i, page in enumerate(pages, 1):
            img = process_page(page['path'], page, max_side=max_side)
            data, ext = _encode(img, jpeg_q)
            dest = unique_path(out_dir, f'{safe} {i:02d}.{ext}')
            dest.write_bytes(data)
            outs.append(dest)
            tick(i)
        return outs

    doc = fitz.open()
    if id_card:
        pw, ph = PAGE_SIZES['letter' if page_size == 'letter' else 'a4']
        cw, ch = ID_CARD_MM[0] * MM, ID_CARD_MM[1] * MM
        for start in range(0, n, 2):
            sheet = doc.new_page(width=pw, height=ph)
            for slot, page in enumerate(pages[start:start + 2]):
                img = process_page(page['path'], page, max_side=1600)
                if img.shape[0] > img.shape[1]:      # cards lie flat on the sheet
                    img = rotate(img, 90)
                data, _ = _encode(img, max(jpeg_q, 85))
                top = ph * (0.16 if slot == 0 else 0.52)
                rect = fitz.Rect((pw - cw) / 2, top, (pw + cw) / 2, top + ch)
                sheet.insert_image(rect, stream=data)
                if ocr:
                    _ocr_overlay(sheet, img, rect)
                tick(start + slot + 1, f'{start + slot + 1}/{n}')
    else:
        for i, page in enumerate(pages, 1):
            img = process_page(page['path'], page, max_side=max_side)
            h, w = img.shape[:2]
            pw, ph = _page_rect(page_size, w, h)
            pdf_page = doc.new_page(width=pw, height=ph)
            s = min(pw / w, ph / h)
            iw, ih = w * s, h * s
            rect = fitz.Rect((pw - iw) / 2, (ph - ih) / 2, (pw + iw) / 2, (ph + ih) / 2)
            data, _ = _encode(img, jpeg_q)
            pdf_page.insert_image(rect, stream=data)
            if ocr:
                _ocr_overlay(pdf_page, img, rect)
            tick(i, f'{i}/{n}')
    dest = unique_path(out_dir, f'{safe}.pdf')
    doc.set_metadata({'title': safe, 'producer': 'Morphix', 'creator': 'Morphix scanner'})
    doc.save(str(dest), garbage=4, deflate=True)
    doc.close()
    return [dest]


# --------------------------------------------------------------------- QR read
def read_qr_codes(paths, out_dir, progress=None):
    """Read QR codes and barcodes in pictures; writes one text file with what each one says."""
    from PIL import Image
    import qr_maker
    from core_ops import unique_path
    found = []
    for i, path in enumerate(paths, 1):
        img = Image.fromarray(load_rgb(path, max_side=3000))
        found.append((Path(path).name, list(dict.fromkeys(qr_maker.decode(img)))))
        if progress:
            progress(round(i * 100 / len(paths)))
    if not any(t for _, t in found):
        raise ValueError('No QR code was found in the selected picture(s).')
    lines = []
    for name, texts in found:
        if len(paths) > 1:
            lines.append(f'===== {name} =====')
        lines.extend(texts or ['(no QR code found)'])
        lines.append('')
    dest = unique_path(Path(out_dir), 'QR codes.txt' if len(paths) > 1 else f'{Path(paths[0]).stem}_QR.txt')
    dest.write_text('\n'.join(lines).strip() + '\n', encoding='utf-8-sig')
    return [dest]
