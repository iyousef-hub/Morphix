"""Morphix interactive diagnostic. Run with: python gui_selftest.py

Checks physical Qt buttons (not just wheel painting), context switching, and
conversion. Runs locally without touching the user's own files.
"""
from pathlib import Path
import tempfile
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QToolButton
from PySide6.QtTest import QTest
from PIL import Image
import fitz

from quickwheel import WheelWindow
from file_intelligence import file_summary, selection_profile


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='morphix_gui_test_') as tmp:
        folder = Path(tmp)
        image_path = folder / 'sample.png'
        Image.new('RGB', (48, 32), '#4a95e8').save(image_path)
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text((50, 60), 'Morphix PDF test')
            pdf_path = folder / 'sample.pdf'
            pdf.save(pdf_path)

        wheel = WheelWindow()
        clicked = []
        wheel.action_requested.connect(clicked.append)
        wheel.set_context([str(image_path)], 'image_single', ['images_pdf','image_jpg','image_png'])
        wheel.display()
        app.processEvents()
        button = wheel.findChild(QToolButton, 'wheel_action_images_pdf')
        assert button is not None, 'The real Make PDF button is missing'
        assert button.isVisible(), 'The Make PDF button is invisible'
        QTest.mouseClick(button, Qt.LeftButton)
        app.processEvents()
        assert clicked == ['images_pdf'], f'Button did not emit conversion action: {clicked}'
        print('PASS: actual Qt Make PDF button accepts a simulated click', flush=True)

        from main import execute
        class Progress:
            def emit(self, _value): pass
        outputs = execute('images_pdf', [str(image_path)], str(folder), Progress())
        assert len(outputs) == 1 and Path(outputs[0]).is_file(), outputs
        with fitz.open(outputs[0]) as converted:
            assert len(converted) == 1
        print('PASS: a real PNG was converted into a one-page PDF', flush=True)

        paths = [str(pdf_path), str(image_path)]
        assert selection_profile(paths) == 'mixed'
        assert file_summary(paths) == ['1 PDF', '1 PNG']
        wheel.set_context(paths, 'mixed', ['zip_files','tar_gz_files','rar_files'])
        assert wheel.findChild(QToolButton, 'wheel_action_zip_files') is not None
        assert wheel.findChild(QToolButton, 'wheel_action_images_pdf') is None or not wheel.findChild(QToolButton, 'wheel_action_images_pdf').isVisible()
        print('PASS: mixed PDF+PNG context switches to archive actions', flush=True)
        wheel.hide()
        wheel.deleteLater()
        app.processEvents()
    print('PASS: all Morphix GUI self-tests completed', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
