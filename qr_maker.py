"""QR codes (Morphix 1.10): turn a link (Google Drive, OneDrive, a website…), text, a Wi-Fi
network or a contact card into a clean QR code — PNG, SVG or PDF. Offline."""
from __future__ import annotations

import base64
import io
from pathlib import Path

STYLES = ('square', 'rounded', 'dots')


# --------------------------------------------------------------------- content
def wifi_payload(ssid, password='', security='WPA', hidden=False):
    def esc(v):
        return ''.join('\\' + c if c in '\\;,:"' else c for c in str(v))
    sec = security if security in ('WPA', 'WEP') and password else 'nopass'
    return f'WIFI:T:{sec};S:{esc(ssid)};' + (f'P:{esc(password)};' if password else '') + \
        ('H:true;' if hidden else '') + ';'


def contact_payload(name='', phone='', email='', company='', website=''):
    lines = ['BEGIN:VCARD', 'VERSION:3.0']
    if name:
        lines += [f'N:{name};;;;', f'FN:{name}']
    if company:
        lines.append(f'ORG:{company}')
    if phone:
        lines.append(f'TEL;TYPE=CELL:{phone}')
    if email:
        lines.append(f'EMAIL:{email}')
    if website:
        lines.append(f'URL:{website}')
    lines.append('END:VCARD')
    return '\n'.join(lines)


def link_tip(text):
    """A short reminder for cloud links, so people who scan can actually open the file."""
    t = (text or '').lower()
    if 'drive.google.com' in t or 'docs.google.com' in t:
        return 'drive'
    if 'onedrive' in t or '1drv.ms' in t or 'sharepoint.com' in t:
        return 'onedrive'
    if 'dropbox.com' in t:
        return 'dropbox'
    if 'icloud.com' in t:
        return 'icloud'
    return None


# --------------------------------------------------------------------- matrix
def matrix(text, logo=False):
    """QR modules as a list of rows of booleans (no quiet zone)."""
    import segno
    if not text:
        raise ValueError('Type a link or some text first.')
    qr = segno.make(text, error='h' if logo else 'm', boost_error=not logo, micro=False)
    return [[bool(v) for v in row] for row in qr.matrix]


def _is_finder(r, c, n):
    return (r < 7 and c < 7) or (r < 7 and c >= n - 7) or (r >= n - 7 and c < 7)


def _shapes(mat, style):
    """Drawing instructions in module units: ('rect'|'round'|'dot', x, y, w, h, radius)."""
    n = len(mat)
    out = []
    for fr, fc in ((0, 0), (0, n - 7), (n - 7, 0)):
        r_out = 0 if style == 'square' else 2.0
        r_in = 0 if style == 'square' else 1.0
        out.append(('frame', fc, fr, 7, 7, r_out))
        out.append(('round' if r_in else 'rect', fc + 2, fr + 2, 3, 3, r_in))
    for r in range(n):
        for c in range(n):
            if not mat[r][c] or _is_finder(r, c, n):
                continue
            if style == 'dots':
                out.append(('dot', c + 0.06, r + 0.06, 0.88, 0.88, 0.44))
            elif style == 'rounded':
                out.append(('round', c + 0.04, r + 0.04, 0.92, 0.92, 0.3))
            else:
                out.append(('rect', c, r, 1, 1, 0))
    return out


def _logo_box(n):
    """Centre area (in modules) left free for a logo: about 22 % of the width."""
    size = max(5, int(round(n * 0.22)))
    if (n - size) % 2:
        size += 1
    start = (n - size) / 2
    return start, size


def _clear_logo(mat):
    n = len(mat)
    start, size = _logo_box(n)
    a, b = int(start) - 1, int(start + size) + 1
    return [[False if a <= r < b and a <= c < b else v for c, v in enumerate(row)] for r, row in enumerate(mat)]


# --------------------------------------------------------------------- PNG
def render(text, *, style='rounded', fg='#0B1A2E', bg='#FFFFFF', transparent=False, logo=None,
           size=1024, caption='', border=4):
    """The QR code as a PIL image."""
    from PIL import Image, ImageDraw, ImageFont
    mat = matrix(text, logo=bool(logo))
    if logo:
        mat = _clear_logo(mat)
    n = len(mat)
    total = n + 2 * border
    scale = max(4, size // total)
    px = total * scale
    cap_h = int(scale * 4.2) if caption else 0
    back = (0, 0, 0, 0) if transparent else bg
    img = Image.new('RGBA', (px, px + cap_h), back)
    d = ImageDraw.Draw(img)
    off = border * scale

    def box(x, y, w, h):
        return [off + x * scale, off + y * scale, off + (x + w) * scale - 1, off + (y + h) * scale - 1]

    for kind, x, y, w, h, rad in _shapes(mat, style):
        if kind == 'frame':
            d.rounded_rectangle(box(x, y, w, h), radius=rad * scale, fill=fg)
            d.rounded_rectangle(box(x + 1, y + 1, w - 2, h - 2), radius=max(0, (rad - 0.8)) * scale,
                                fill=(0, 0, 0, 0) if transparent else bg)
        elif kind == 'dot':
            d.ellipse(box(x, y, w, h), fill=fg)
        elif kind == 'round':
            d.rounded_rectangle(box(x, y, w, h), radius=rad * scale, fill=fg)
        else:
            d.rectangle(box(x, y, w, h), fill=fg)
    if logo:
        start, lsize = _logo_box(n)
        with Image.open(logo) as li:
            li = li.convert('RGBA')
            inner = int(lsize * scale * 0.86)
            li.thumbnail((inner, inner), Image.LANCZOS)
            pad = [off + start * scale, off + start * scale, off + (start + lsize) * scale, off + (start + lsize) * scale]
            d.rounded_rectangle(pad, radius=scale * 1.2, fill=bg if not transparent else '#FFFFFF')
            cx = int(off + (start + lsize / 2) * scale)
            img.alpha_composite(li, (cx - li.width // 2, cx - li.height // 2))
    if caption:
        font_px = int(scale * 2.2)
        cap = _qt_caption(caption, font_px, fg, px) if _needs_qt(caption) else None
        if cap is not None:
            img.alpha_composite(cap, (0, int(px - scale * 1.2)))
        else:
            font = _font(font_px)
            tw = d.textlength(caption, font=font)
            d.text(((px - tw) / 2, px - scale * 1.2), caption, fill=fg, font=font)
    return img


def _needs_qt(text):
    """Pillow joins Arabic letters only with its optional text engine; Qt always can."""
    if text.isascii():
        return False
    try:
        from PIL import features
        return not features.check('raqm')
    except Exception:
        return True


def _qt_caption(text, font_px, color, width):
    try:
        from PySide6.QtGui import QGuiApplication, QImage, QPainter, QFont, QColor
        from PySide6.QtCore import Qt, QRect
        from PIL import Image
        if QGuiApplication.instance() is None:
            return None
        h = int(font_px * 1.8)
        qimg = QImage(width, h, QImage.Format_RGBA8888)
        qimg.fill(Qt.transparent)
        p = QPainter(qimg)
        p.setRenderHint(QPainter.TextAntialiasing)
        f = QFont('IBM Plex Sans Arabic'); f.setPixelSize(font_px); f.setWeight(QFont.DemiBold)
        p.setFont(f); p.setPen(QColor(color))
        p.drawText(QRect(0, 0, width, h), Qt.AlignHCenter | Qt.AlignTop, text)
        p.end()
        return Image.frombuffer('RGBA', (width, h), bytes(qimg.constBits()), 'raw', 'RGBA', qimg.bytesPerLine(), 1)
    except Exception:
        return None


def _font(size):
    from PIL import ImageFont
    for base in (Path(__file__).resolve().parent / 'assets' / 'fonts',):
        f = base / 'IBMPlexSansArabic-SemiBold.ttf'
        if f.is_file():
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default()


# --------------------------------------------------------------------- SVG
def to_svg(text, *, style='rounded', fg='#0B1A2E', bg='#FFFFFF', transparent=False, logo=None, caption='',
           border=4):
    mat = matrix(text, logo=bool(logo))
    if logo:
        mat = _clear_logo(mat)
    n = len(mat)
    total = n + 2 * border
    cap = 4.2 if caption else 0
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
             f'viewBox="0 0 {total} {total + cap}" width="{total * 10}" height="{(total + cap) * 10}">']
    if not transparent:
        parts.append(f'<rect width="{total}" height="{total + cap}" fill="{bg}"/>')
    hole = 'none' if transparent else bg
    for kind, x, y, w, h, rad in _shapes(mat, style):
        x, y = x + border, y + border
        if kind == 'frame':
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rad}" fill="{fg}"/>')
            parts.append(f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" '
                         f'rx="{max(0, rad - 0.8)}" fill="{hole if hole != "none" else "#FFFFFF"}"/>')
        elif kind == 'dot':
            parts.append(f'<circle cx="{x + w / 2:.3f}" cy="{y + h / 2:.3f}" r="{w / 2:.3f}" fill="{fg}"/>')
        elif kind == 'round':
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rad}" fill="{fg}"/>')
        else:
            parts.append(f'<rect x="{x}" y="{y}" width="1.02" height="1.02" fill="{fg}"/>')
    if logo:
        from PIL import Image
        start, size = _logo_box(n)
        s = start + border
        with Image.open(logo) as li:
            li = li.convert('RGBA')
            li.thumbnail((512, 512))
            buf = io.BytesIO(); li.save(buf, 'PNG')
        data = base64.b64encode(buf.getvalue()).decode()
        parts.append(f'<rect x="{s}" y="{s}" width="{size}" height="{size}" rx="1.2" '
                     f'fill="{bg if not transparent else "#FFFFFF"}"/>')
        inner = size * 0.86
        parts.append(f'<image x="{s + (size - inner) / 2}" y="{s + (size - inner) / 2}" width="{inner}" '
                     f'height="{inner}" preserveAspectRatio="xMidYMid meet" '
                     f'xlink:href="data:image/png;base64,{data}"/>')
    if caption:
        from xml.sax.saxutils import escape
        parts.append(f'<text x="{total / 2}" y="{total + 1.6}" font-family="IBM Plex Sans Arabic, Arial, sans-serif" '
                     f'font-size="2.2" font-weight="600" text-anchor="middle" fill="{fg}">{escape(caption)}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def save(text, dest, fmt, **style):
    """Write the QR as PNG, SVG or PDF. Returns the path."""
    dest = Path(dest)
    if fmt == 'svg':
        dest.write_text(to_svg(text, **{k: v for k, v in style.items() if k != 'size'}), encoding='utf-8')
    elif fmt == 'pdf':
        import pymupdf as fitz
        img = render(text, **{**style, 'size': 2048})
        buf = io.BytesIO(); img.save(buf, 'PNG')
        doc = fitz.open()
        page = doc.new_page(width=595.28, height=841.89)
        w = 360.0
        h = w * img.height / img.width
        rect = fitz.Rect((595.28 - w) / 2, 150, (595.28 + w) / 2, 150 + h)
        page.insert_image(rect, stream=buf.getvalue())
        doc.save(str(dest), deflate=True)
        doc.close()
    else:
        render(text, **style).save(dest, 'PNG', optimize=True)
    return dest


def decode(img):
    """Texts of the QR codes / barcodes a reader finds in a PIL image ([] when none)."""
    from PIL import Image
    rgb = img
    if img.mode in ('RGBA', 'LA', 'P'):
        rgba = img.convert('RGBA')
        rgb = Image.new('RGB', rgba.size, 'white')
        rgb.paste(rgba, mask=rgba.split()[-1])
    elif img.mode != 'RGB':
        rgb = img.convert('RGB')
    try:
        import zxingcpp
        return [r.text for r in zxingcpp.read_barcodes(rgb) if r.text]
    except ImportError:
        pass
    import cv2
    import numpy as np
    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    ok, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(bgr)
    return [t for t in texts if t] if ok else []


def verify(img):
    """The text a QR reader gets back from the rendered picture ('' when unreadable)."""
    try:
        texts = decode(img)
        return texts[0] if texts else ''
    except Exception:
        return None
