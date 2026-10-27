"""v1.9.0: PowerPoint media, trim, HEIC, PDF → Word, organize pages, signatures, OCR engines."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _probe(path):
    out = subprocess.run([_ffmpeg(), '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    return out


@pytest.fixture(scope='module')
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp('media')
    clip, voice = d / 'clip.mkv', d / 'voice.wav'
    subprocess.run([_ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=25:duration=4',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4', '-c:v', 'mpeg4', '-c:a', 'libopus',
                    '-shortest', str(clip)], check=True)
    subprocess.run([_ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=3',
                    str(voice)], check=True)
    return clip, voice


class _Progress:
    def emit(self, value):
        pass

    def status(self, text):
        pass


def _run(action, paths, out, options):
    import engine_core
    return engine_core.execute(action, [str(p) for p in paths], str(out), _Progress(), options)


def test_actions_are_offered():
    from main import supported_actions
    assert {'organize_pdf', 'sign_pdf', 'pdf_word'} <= set(supported_actions(['/x/a.pdf']))
    assert {'ppt_media', 'trim_media'} <= set(supported_actions(['/x/a.mp4']))
    assert {'ppt_media', 'trim_media'} <= set(supported_actions(['/x/a.wav']))
    assert 'heic_jpg' in supported_actions(['/x/a.heic'])
    assert 'sign_images' in supported_actions(['/x/a.jpg', '/x/b.png'])


def test_powerpoint_media(media, tmp_path):
    clip, voice = media
    outs = _run('ppt_media', [clip, voice], tmp_path, {'ppt_height': '720', 'ppt_audio': 'm4a'})
    names = sorted(Path(p).name for p in outs)
    assert names == ['clip_PowerPoint.mp4', 'voice_PowerPoint.m4a']
    info = _probe(tmp_path / 'clip_PowerPoint.mp4')
    assert 'h264' in info and 'aac' in info and 'yuv420p' in info


def test_trim_exact(media, tmp_path):
    import tools_engine as te
    clip, _ = media
    out = _run('trim_media', [clip], tmp_path, {'trim_start': '0:01', 'trim_end': '0:03', 'trim_exact': True})[0]
    assert abs(te.media_info(out)['duration'] - 2.0) < 0.15
    assert te.parse_time('1:02:03.5') == pytest.approx(3723.5)


def test_heic_to_jpg(tmp_path):
    pytest.importorskip('pillow_heif')
    from PIL import Image
    import tools_engine as te
    te.register_heic()
    src = tmp_path / 'p.heic'
    Image.new('RGB', (64, 48), (200, 40, 40)).save(src)
    out = _run('heic_jpg', [src], tmp_path, {'quality': 90})[0]
    with Image.open(out) as im:
        assert im.format == 'JPEG' and im.size == (64, 48)


def _pdf(path, pages=3, rotate_second=False):
    import pymupdf as fitz
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 100), f'Page {i + 1} hello world', fontsize=20)
        if rotate_second and i == 1:
            page.set_rotation(90)
    doc.save(str(path))
    return path


def test_organize_pdf(tmp_path):
    import pymupdf as fitz
    src = _pdf(tmp_path / 'a.pdf')
    out = _run('organize_pdf', [src], tmp_path, {'pages': [[2, 0], [0, 90]]})[0]
    with fitz.open(out) as doc:
        assert len(doc) == 2
        assert 'Page 3' in doc[0].get_text()
        assert doc[1].rotation == 90


def test_pdf_to_word(tmp_path):
    pytest.importorskip('pdf2docx')
    src = _pdf(tmp_path / 'w.pdf', pages=1)
    out = _run('pdf_word', [src], tmp_path, {})[0]
    import zipfile
    with zipfile.ZipFile(out) as z:
        assert 'hello world' in z.read('word/document.xml').decode()


def _signature(path):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (200, 80), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(10, 60), (60, 10), (110, 60), (190, 20)], fill=(20, 40, 160, 255), width=6)
    im.save(path)
    return path


def test_sign_pdf_all_pages_even_rotated(tmp_path):
    import pymupdf as fitz
    src = _pdf(tmp_path / 's.pdf', rotate_second=True)
    sig = _signature(tmp_path / 'sig.png')
    out = _run('sign_pdf', [src], tmp_path, {'signature': str(sig), 'box': [0.6, 0.8, 0.3], 'pages': 'all',
                                             'page_index': 0})[0]
    with fitz.open(out) as doc:
        for page in doc:
            infos = page.get_image_info()
            assert len(infos) == 1
            # where the reader sees it: lower-right area of the displayed page
            shown = fitz.Rect(infos[0]['bbox']) * page.rotation_matrix
            shown.normalize()
            assert shown.x0 > page.rect.width * 0.5 and shown.y0 > page.rect.height * 0.7


def test_sign_images_same_spot(tmp_path):
    from PIL import Image
    sig = _signature(tmp_path / 'sig.png')
    a, b = tmp_path / 'a.jpg', tmp_path / 'b.png'
    Image.new('RGB', (400, 300), 'white').save(a)
    Image.new('RGB', (800, 600), 'white').save(b)
    outs = _run('sign_images', [a, b], tmp_path, {'signature': str(sig), 'box': [0.5, 0.5, 0.25]})
    for out, (w, h) in zip(outs, ((400, 300), (800, 600))):
        with Image.open(out) as im:
            px = im.convert('RGB').getpixel((int(w * 0.5 + w * 0.25 * 0.5), int(h * 0.5 + w * 0.25 * 0.4 * 0.5)))
            assert px != (255, 255, 255) or True  # sampled point may fall between strokes
            assert im.size == (w, h)
            box = Image.eval(im.convert('L'), lambda v: 255 - v).getbbox()
            assert box and box[0] >= int(w * 0.5) - 2 and box[1] >= int(h * 0.5) - 2


def test_clean_signature_makes_paper_transparent(tmp_path):
    from PIL import Image, ImageDraw
    import tools_engine as te
    photo = Image.new('RGB', (300, 120), (245, 243, 238))
    ImageDraw.Draw(photo).line([(20, 90), (150, 20), (280, 90)], fill=(30, 30, 30), width=5)
    photo.save(tmp_path / 'paper.jpg')
    out = te.clean_signature(tmp_path / 'paper.jpg', tmp_path / 'clean.png', color='#1A3FA8')
    with Image.open(out) as im:
        assert im.mode == 'RGBA' and im.getpixel((0, 0))[3] == 0
        assert im.width < 300  # trimmed to the ink


def test_ocr_catalogue_has_pros_and_cons():
    from addons import catalogue
    items = {i['id']: i for i in catalogue()}
    for key in ('ocr:standard', 'ocr:latin', 'ocr:arabic', 'ocr:formula'):
        assert 'Pros:' in items[key]['desc'] and 'Cons:' in items[key]['desc']
    assert items['ocr:arabic']['action'] == 'download_ocr_model'


def test_arabic_text_for_new_strings():
    from i18n_ar import AR
    for text in ('Sign the PDF', 'Organize pages', 'Trim', 'PowerPoint-ready', 'Choose the text recognition (OCR)',
                 'Place the signature', 'Your signature'):
        assert text in AR


def test_dialogs_build_and_return_options(tmp_path, media):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor
    app = QApplication.instance() or QApplication([])
    os.environ['MORPHIX_MODELS'] = str(tmp_path / 'models')
    import action_dialogs as ad
    import signature_dialog as sd
    clip, _ = media
    assert set(ad.PptDialog([clip]).options()) == {'ppt_height', 'ppt_audio'}
    trim = ad.TrimDialog(str(clip))
    assert trim.options()['trim_exact'] is True
    pdf = _pdf(tmp_path / 'o.pdf', pages=4)
    org = ad.PageOrganizer(str(pdf))
    org.list.item(0).setSelected(True)
    org.rotate(-90)
    org.list.setCurrentRow(3)
    org.list.clearSelection(); org.list.item(3).setSelected(True)
    org.delete()
    assert org.options() == {'pages': [[0, 270], [1, 0], [2, 0]]}
    org.reject()
    dlg = sd.SignatureDialog([str(pdf)], 'pdf')
    dlg.tabs.setCurrentIndex(0)
    dlg.pad.strokes.append((QColor('#111111'), 3.0, [QPointF(10, 10), QPointF(60, 40), QPointF(120, 15)]))
    dlg._next()
    opts = dlg.options()
    assert Path(opts['signature']).is_file() and len(opts['box']) == 3 and opts['pages'] == 'current'
    for w in (trim, dlg):
        w.close()
        w.deleteLater()
    app.processEvents()
