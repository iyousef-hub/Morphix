"""v1.10: document scanner, phone → computer over Wi-Fi, QR codes."""
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

def _camera_corners(ax=0.35, ay=0.12, az=0.06, W=1500, H=2000, f=1600, paper=(21.0, 29.7), dist=46):
    """Where an A4 sheet's corners land in a real (pinhole) camera photo taken at an angle."""
    import numpy as np
    rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    w, h = paper
    pts = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]])
    pts = pts @ (rz @ ry @ rx).T + np.array([0.5, -0.8, dist])
    return [[(f * x / z + W / 2) / W, (f * y / z + H / 2) / H] for x, y, z in pts]


CORNERS = _camera_corners()


def _document(w=620, h=877):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (250, 248, 242))
    d = ImageDraw.Draw(im)
    for i in range(20):
        d.rectangle((50, 60 + i * 38, 50 + (i * 37) % 300 + 220, 74 + i * 38), fill=(25, 25, 35))
    return im


def _photo(path, corners=CORNERS, size=(1500, 2000)):
    """A sheet of paper photographed at an angle on a brown table, with uneven light."""
    import cv2
    import numpy as np
    W, H = size
    doc = np.asarray(_document())
    h, w = doc.shape[:2]
    quad = np.float32([[x * W, y * H] for x, y in corners])
    m = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), quad)
    warped = cv2.warpPerspective(doc, m, (W, H))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), m, (W, H))
    rng = np.random.default_rng(3)
    table = (rng.normal(0, 10, (H, W, 3)) + np.array([96, 72, 52])).clip(0, 255).astype('uint8')
    out = np.where(mask[..., None] > 0, warped, table).astype('float32')
    xx = np.mgrid[0:H, 0:W][1]
    out *= (0.6 + 0.4 * xx / W)[..., None]
    from PIL import Image
    Image.fromarray(out.clip(0, 255).astype('uint8')).save(path, quality=92)
    return path


@pytest.fixture(scope='module')
def photo(tmp_path_factory):
    return _photo(tmp_path_factory.mktemp('scan') / 'page.jpg')


def test_actions_offered_for_pictures():
    from main import supported_actions
    acts = supported_actions(['/x/a.jpg'])
    assert acts.count('scan_document') == 1 and 'read_qr' in acts
    assert 'scan_document' in supported_actions(['/x/a.jpg', '/x/b.heic'])
    assert 'scan_document' not in supported_actions(['/x/a.pdf'])


def test_finds_the_sheet(photo):
    import scan_engine as se
    corners, found = se.find_document(se.load_rgb(photo))
    assert found
    for (x, y), (ex, ey) in zip(corners, CORNERS):
        assert abs(x - ex) < 0.02 and abs(y - ey) < 0.02


def test_plain_picture_uses_whole_photo(tmp_path):
    from PIL import Image
    import scan_engine as se
    Image.new('RGB', (800, 600), (200, 210, 230)).save(tmp_path / 'flat.png')
    corners, found = se.find_document(se.load_rgb(tmp_path / 'flat.png'))
    assert not found and corners == se.full_corners()


def test_filters_make_clean_pages(photo):
    import numpy as np
    import scan_engine as se
    corners, _ = se.find_document(se.load_rgb(photo))
    for name in se.FILTERS:
        img = se.process_page(photo, {'corners': corners, 'filter': name}, max_side=1200)
        h, w = img.shape[:2]
        assert abs(h / w - 2 ** 0.5) < 0.02               # the true A4 shape, perspective undone
        if name != 'original':
            gray = img if img.ndim == 2 else img.mean(axis=2)
            assert np.percentile(gray, 60) > 225           # paper turned white, shadows gone
            # no dark strip of table left along the edges
            assert gray[:, :4].mean() > 150 and gray[:, -4:].mean() > 150
    bw = se.process_page(photo, {'corners': corners, 'filter': 'bw'}, max_side=1200)
    assert set(np.unique(bw)) <= {0, 255}


def test_pdf_a4_and_id_card_and_images(photo, tmp_path):
    import pymupdf as fitz
    import scan_engine as se
    corners, _ = se.find_document(se.load_rgb(photo))
    pages = [{'path': str(photo), 'corners': corners, 'rotation': 0, 'filter': 'bw'},
             {'path': str(photo), 'corners': corners, 'rotation': 90, 'filter': 'enhanced'}]
    out = se.build_scan(pages, tmp_path, name='My scan')[0]
    assert out.name == 'My scan.pdf'
    with fitz.open(out) as doc:
        assert len(doc) == 2
        assert round(doc[0].rect.width) == 595 and round(doc[0].rect.height) == 842
        assert doc[1].rect.width > doc[1].rect.height           # turned sideways → landscape page
    assert out.stat().st_size < 1_500_000
    card = se.build_scan(pages, tmp_path, name='Card', id_card=True)[0]
    with fitz.open(card) as doc:
        assert len(doc) == 1 and len(doc[0].get_images()) == 2
    imgs = se.build_scan(pages, tmp_path, name='Pics', output='images')
    assert [p.suffix for p in imgs] == ['.png', '.jpg']


def test_searchable_scan(photo, tmp_path):
    import pymupdf as fitz
    from PIL import Image, ImageDraw, ImageFont
    import scan_engine as se
    im = Image.new('RGB', (1240, 1754), 'white')
    font = ImageFont.truetype(str(ROOT / 'assets' / 'fonts' / 'IBMPlexSansArabic-Bold.ttf'), 70)
    ImageDraw.Draw(im).text((120, 200), 'Invoice 2026', fill='black', font=font)
    im.save(tmp_path / 'clean.png')
    out = se.build_scan([{'path': str(tmp_path / 'clean.png'), 'corners': se.full_corners(), 'filter': 'gray'}],
                        tmp_path, name='Text', ocr=True)[0]
    with fitz.open(out) as doc:
        assert 'Invoice' in doc[0].get_text()


def test_qr_styles_scan_back(tmp_path):
    import qr_maker
    url = 'https://drive.google.com/file/d/1AbCdEf/view?usp=sharing'
    for style in qr_maker.STYLES:
        for logo in (None, str(ROOT / 'assets' / 'morphix_logo.png')):
            img = qr_maker.render(url, style=style, logo=logo, caption='Scan me', size=800)
            assert qr_maker.verify(img) == url, (style, logo)
    assert qr_maker.link_tip(url) == 'drive'
    for fmt in ('png', 'svg', 'pdf'):
        dest = qr_maker.save(url, tmp_path / f'q.{fmt}', fmt, style='dots')
        assert dest.stat().st_size > 500
    assert qr_maker.wifi_payload('Home;Net', 'p:1') == 'WIFI:T:WPA;S:Home\\;Net;P:p\\:1;;'
    assert 'TEL;TYPE=CELL:0500' in qr_maker.contact_payload('Yousef', '0500')


def test_read_qr(tmp_path):
    import qr_maker
    import scan_engine as se
    qr_maker.render('Morphix 1.10', style='rounded').save(tmp_path / 'code.png')
    out = se.read_qr_codes([tmp_path / 'code.png'], tmp_path)[0]
    assert out.read_text(encoding='utf-8-sig').strip() == 'Morphix 1.10'


def test_phone_server(tmp_path):
    import phone_transfer as pt
    got = []
    server = pt.PhoneServer(tmp_path / 'in', got.append, language='ar', computer='Test-PC')
    port = server.start()
    try:
        base = f'http://127.0.0.1:{port}/{server.key}'
        page = urllib.request.urlopen(base, timeout=5).read().decode()
        assert 'dir="rtl"' in page and 'Test-PC' in page
        for name in ('IMG_1.JPG', '../../x.jpg', 'IMG_1.JPG'):
            req = urllib.request.Request(base + '/upload', data=b'\xff\xd8 hello', method='POST',
                                         headers={'X-File-Name': urllib.parse.quote(name)})
            assert urllib.request.urlopen(req, timeout=5).status == 200
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f'http://127.0.0.1:{port}/wrong', timeout=5)
    finally:
        server.stop()
    names = sorted(Path(p).name for p in got)
    assert names == ['IMG_1 (2).JPG', 'IMG_1.JPG', 'x.jpg']
    assert all(Path(p).parent == tmp_path / 'in' for p in got)
    assert not list((tmp_path / 'in').glob('*.part'))


def test_phone_resumes_big_files(tmp_path):
    import io
    import phone_transfer as pt
    got = []
    server = pt.PhoneServer(tmp_path / 'in', got.append)
    data = os.urandom(30_000)
    assert server.receive('abcdef12', 'clip.mov', 30_000, 0, 10_000, 1_700_000_000_000 / 1000,
                          io.BytesIO(data[:10_000]))[0] == 200
    # the phone lost a reply and jumps ahead: Morphix tells it where to continue
    assert server.receive('abcdef12', 'clip.mov', 30_000, 20_000, 10_000, 0, io.BytesIO(data[20_000:])) == \
        (409, {'received': 10_000})

    class Cut(io.BytesIO):          # Wi-Fi drops in the middle of a piece
        def read(self, n=-1):
            return super().read(min(n, 4000)) if self.tell() < 4000 else b''
    assert server.receive('abcdef12', 'clip.mov', 30_000, 10_000, 10_000, 0, Cut(data[10_000:20_000]))[0] == 400
    assert server.receive('abcdef12', 'clip.mov', 30_000, 10_000, 10_000, 0, io.BytesIO(data[10_000:20_000]))[1] == \
        {'received': 20_000}
    code, body = server.receive('abcdef12', 'clip.mov', 30_000, 20_000, 10_000, 0, io.BytesIO(data[20_000:]))
    assert code == 200 and body['done']
    assert Path(got[0]).read_bytes() == data                       # byte-for-byte, full quality
    assert int(Path(got[0]).stat().st_mtime) == 1_700_000_000       # the file keeps its own date
    assert [p.name for p in (tmp_path / 'in').iterdir()] == ['clip.mov']
    assert 'Format' in pt.page_html('en', 'PC', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)')
    assert 'class="ios"' not in pt.page_html('en', 'PC', 'Mozilla/5.0 (Linux; Android 14)')


def test_windows_build(tmp_path, photo):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from scan_dialog import ScanDialog
    from qr_dialog import QrDialog
    from phone_transfer import PhoneDialog
    d = ScanDialog([str(photo), str(photo)])
    while d._pending:
        d._detect_next()
    d.list.setCurrentRow(1)
    d._rotate(90)
    opts = d.options()
    assert len(opts['scan_pages']) == 2 and opts['scan_pages'][1]['rotation'] == 90
    assert opts['scan_pages'][0]['corners'] != [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    d._delete()
    assert len(d.options()['scan_pages']) == 1
    q = QrDialog(text='https://example.com')
    q._update()
    assert q.payload() == 'https://example.com' and q.save_btn.isEnabled()
    q.kind.button(1).click(); q.ssid.setText('Home'); q._update()
    assert q.payload().startswith('WIFI:')
    p = PhoneDialog(purpose='scan', folder=tmp_path / 'phone')
    assert p.server.port
    p.reject()
    assert p.server.httpd is None
    for w in (d, q):
        w.close(); w.deleteLater()
    app.processEvents()


def test_arabic_text():
    from i18n_ar import AR
    for text in ('Scan documents', 'From my phone', 'QR code', 'Scan as a document (straighten · clean · PDF)',
                 'Black & white', 'Waiting for your phone…', 'Checked: it scans correctly.'):
        assert text in AR
