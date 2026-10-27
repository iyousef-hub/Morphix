"""Smoke test of a packaged Morphix build (used by the GitHub builds).

    python tools/smoke_build.py <command that starts Morphix> [--office] [--downloads]

Creates sample files, runs every engine through the built app in worker mode
(--morphix-worker) and fails when any of them does not complete.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


def samples(w: Path):
    import imageio_ffmpeg
    import openpyxl
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    d = pymupdf.open()
    for i in range(3):
        d.new_page().insert_text((72, 100), f'Morphix smoke test page {i + 1}. ' * 3, fontsize=14)
    d.save(str(w / 'a.pdf'))
    wb = openpyxl.Workbook(); wb.active.append(['a', 1]); wb.save(w / 'b.xlsx')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=10:duration=3',
                    '-f', 'lavfi', '-i', 'sine=duration=3', '-c:v', 'mpeg4', '-shortest', str(w / 'c.mkv')], check=True)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=3',
                    str(w / 'd.wav')], check=True)
    try:
        font = ImageFont.load_default(size=44)
    except TypeError:
        font = ImageFont.load_default()
    img = Image.new('RGB', (900, 200), 'white')
    ImageDraw.Draw(img).text((30, 60), 'Morphix reads this text', fill='black', font=font)
    img.save(w / 'text.png')
    formula = Image.new('RGB', (420, 120), 'white')
    ImageDraw.Draw(formula).text((30, 30), 'E = mc2', fill='black', font=font)
    formula.save(w / 'formula.png')
    Image.new('RGB', (400, 300), (40, 120, 200)).save(w / 'photo.jpg')
    sig = Image.new('RGBA', (200, 80), (0, 0, 0, 0))
    ImageDraw.Draw(sig).line([(10, 60), (60, 10), (110, 60), (190, 20)], fill=(20, 40, 160, 255), width=6)
    sig.save(w / 'sig.png')
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        Image.new('RGB', (64, 48), (200, 40, 40)).save(w / 'p.heic')
        has_heic = True
    except Exception as exc:  # pragma: no cover
        print('HEIC sample unavailable:', exc)
        has_heic = False
    return has_heic


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__); return 2
    app = shlex.split(args[0]) if not Path(args[0]).exists() else [args[0]]
    office = '--office' in sys.argv
    downloads = '--downloads' in sys.argv
    w = Path(tempfile.mkdtemp(prefix='morphix_smoke_'))
    out = w / 'out'; out.mkdir()
    has_heic = samples(w)
    s = lambda n: str(w / n)
    jobs = [
        ('pdf_png_zip', [s('a.pdf')], {}),
        ('ocr_searchable_pdf', [s('a.pdf')], {}),
        ('xlsx_csv', [s('b.xlsx')], {}),
        ('video_mp3', [s('c.mkv')], {}),
        ('ppt_media', [s('c.mkv'), s('d.wav')], {'ppt_height': '720', 'ppt_audio': 'm4a'}),
        ('trim_media', [s('c.mkv')], {'trim_start': '0:00.5', 'trim_end': '0:02', 'trim_exact': True}),
        ('trim_media', [s('d.wav')], {'trim_start': '0:01', 'trim_end': '0:02', 'trim_exact': False}),
        ('pdf_word', [s('a.pdf')], {}),
        ('organize_pdf', [s('a.pdf')], {'pages': [[2, 0], [0, 90]]}),
        ('sign_pdf', [s('a.pdf')], {'signature': s('sig.png'), 'box': [0.6, 0.8, 0.3], 'pages': 'all', 'page_index': 0}),
        ('sign_images', [s('photo.jpg'), s('text.png')], {'signature': s('sig.png'), 'box': [0.5, 0.5, 0.3]}),
        ('ocr_image_text', [s('text.png')], {'ocr_engine': 'accurate', 'ocr_lang': 'latin'}),
        ('extract_pdf_text', [s('a.pdf')], {'ocr_engine': 'accurate', 'ocr_lang': 'latin'}),
    ]
    if has_heic:
        jobs.append(('heic_jpg', [s('p.heic')], {'quality': 90}))
    if office:
        jobs.append(('office_pdf', [s('b.xlsx')], {}))
    if downloads:
        jobs += [
            ('download_ocr_model', [], {'kind': 'ocr_arabic'}),
            ('ocr_image_text', [s('text.png')], {'ocr_engine': 'accurate', 'ocr_lang': 'ar'}),
            ('download_ocr_model', [], {'kind': 'ocr_formula'}),
            ('ocr_image_text', [s('formula.png')], {'ocr_engine': 'formula'}),
        ]
    env = dict(os.environ, MORPHIX_MODELS=str(w / 'models'))
    failures = 0
    for i, (action, paths, options) in enumerate(jobs):
        req = w / f'r{i}.json'
        req.write_text(json.dumps({'action': action, 'paths': paths, 'out_dir': str(out), 'options': options}),
                       encoding='utf-8')
        try:
            proc = subprocess.run(app + ['--morphix-worker', str(req)], capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=900, env=env)
            text = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            text = 'timeout'
        result = [l for l in text.splitlines() if '"completed"' in l or '"failed"' in l]
        line = result[-1] if result else text[-1500:]
        if '"completed"' in line:
            outputs = json.loads(line.split('=', 1)[1]).get('outputs', [])
            print(f'OK    {action}: {[Path(p).name for p in outputs]}')
        else:
            failures += 1
            print(f'FAIL  {action}: {line[:3000]}')
            if os.environ.get('GITHUB_ACTIONS'):
                print(f'::error::smoke {action} failed')
    print(f'{len(jobs) - failures}/{len(jobs)} passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
