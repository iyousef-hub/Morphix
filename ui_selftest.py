"""Build-time check of the packaged app's windows (run with --morphix-ui-selftest DIR).

Opens every 1.9 option window off-screen with sample files, reads its options and
exits 0 when all of them work. Used by the GitHub builds; never shown to users.
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def run(folder):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MORPHIX_MODELS', str(folder / 'models'))
    import pymupdf
    from PIL import Image, ImageDraw
    pdf = folder / 'ui.pdf'
    doc = pymupdf.open()
    for i in range(3):
        doc.new_page().insert_text((72, 100), f'Page {i + 1}', fontsize=30)
    doc.save(str(pdf))
    png = folder / 'ui.png'
    Image.new('RGB', (400, 300), 'white').save(png)
    sig = folder / 'paper_signature.jpg'
    im = Image.new('RGB', (300, 120), (246, 244, 239))
    ImageDraw.Draw(im).line([(20, 90), (150, 20), (280, 90)], fill=(20, 20, 20), width=5)
    im.save(sig)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor
    app = QApplication.instance() or QApplication(sys.argv[:1])
    import i18n
    results = []
    keep = []

    def track(widget):
        keep.append(widget)
        return widget
    report_file = folder / 'ui_selftest.txt'
    report_file.write_text('', encoding='utf-8')

    def note(line):
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def check(name, fn):
        note(f'START {name}')
        try:
            value = fn()
            results.append(f'OK   {name}: {value}')
        except Exception:
            results.append(f'FAIL {name}:\n{traceback.format_exc()}')
        note(results[-1])

    for lang in ('en', 'ar'):
        i18n.set_language(lang, save=False)
        i18n.apply(app)
        import action_dialogs as ad
        import signature_dialog as sd
        from main import supported_actions, ACTIONS

        check(f'{lang} actions', lambda: [ACTIONS[k] for k in supported_actions([str(pdf)]) if k in
                                          ('organize_pdf', 'sign_pdf', 'pdf_word')])
        check(f'{lang} ppt', lambda: track(ad.PptDialog([str(png)])).options())
        check(f'{lang} ocr', lambda: track(ad.OcrChoiceDialog([str(png)], 'ocr_image_text')).options())
        check(f'{lang} ocr pdf', lambda: track(ad.OcrChoiceDialog([str(pdf)], 'extract_pdf_text')).options())

        def organize():
            d = track(ad.PageOrganizer(str(pdf)))
            for _ in range(10):
                app.processEvents()
            d.list.item(0).setSelected(True)
            d.rotate(90)
            out = d.options()
            d.reject()
            assert out['pages'][0] == [0, 90], out
            return out
        check(f'{lang} organize', organize)

        def sign(kind, paths):
            d = track(sd.SignatureDialog(paths, kind))
            d.show()
            d.tabs.setCurrentIndex(0)
            d.pad.strokes.append((QColor('#1A3FA8'), 3.0, [QPointF(20, 40), QPointF(80, 10), QPointF(140, 45)]))
            d._next()
            app.processEvents()
            out = d.options()
            assert Path(out['signature']).is_file(), out
            d.tabs.setCurrentIndex(1)
            d.uploaded = sig
            d._process_upload()
            assert d.upload_preview.path and d.upload_preview.path.is_file()
            d.reject()
            return out
        check(f'{lang} sign pdf', lambda: sign('pdf', [str(pdf)]))
        check(f'{lang} sign images', lambda: sign('image', [str(png), str(png)]))

        def addons():
            from addons import AddonsDialog
            d = track(AddonsDialog())
            d.show(); app.processEvents(); d.close()
            return 'ok'
        check(f'{lang} add-ons', addons)

        def hub_icons():
            import quickwheel
            from PySide6.QtGui import QPixmap, QPainter, QColor
            pix = QPixmap(64, 64)
            painter = QPainter(pix)
            for key in ('ppt_media', 'trim_media', 'heic_jpg', 'pdf_word', 'organize_pdf', 'sign_pdf', 'sign_images'):
                label, kind = quickwheel.WHEEL_LABELS[key]
                quickwheel._draw_action_icon(painter, 32, 32, kind, QColor('#FFFFFF'))
            painter.end()
            return 'ok'
        check(f'{lang} hub icons', hub_icons)

    # Close every window the test opened before Qt shuts down.
    for widget in keep:
        try:
            widget.close()
            widget.deleteLater()
        except Exception:
            pass
    keep.clear()
    for _ in range(3):
        app.processEvents()
    import gc
    gc.collect()
    app.processEvents()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    report = '\n'.join(results)
    print(report, flush=True)
    failed = [r for r in results if r.startswith('FAIL')]
    verdict = ('UI SELFTEST FAILED: %d' % len(failed)) if failed else 'UI SELFTEST OK'
    note(verdict)
    print(verdict, flush=True)
    return 1 if failed else 0
