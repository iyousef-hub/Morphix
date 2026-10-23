"""Run on macOS/Windows after installing requirements:

    python gui_selftest_v14.py

Checks real Qt widgets without user documents. It does not test macOS
Accessibility permission or the OS-global hotkey, which need manual testing.
"""
from pathlib import Path
import tempfile

from PIL import Image
from PySide6.QtWidgets import QApplication
import pymupdf

from range_dialogs import PageRangeDialog
from visual_editor import ImageEditor
from quickwheel import WheelWindow


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='morphix_v14_gui_') as td:
        folder = Path(td)
        image = folder / 'test.png'
        Image.new('RGB', (260, 140), '#55A2E0').save(image)
        # Multi-range UI exposes bounded inputs and + inserts usable ranges.
        ranges = PageRangeDialog(100, separate=True)
        assert ranges.ranges() == [(1, 10)]
        ranges.add_next()
        assert ranges.ranges() == [(1, 10), (11, 100)]
        ranges.add_next()
        assert ranges.ranges() == [(1, 10), (11, 55), (56, 100)]
        assert all(row[1].maximum() == 100 and row[2].maximum() == 100 for row in ranges.rows)
        ranges.close()
        print('PASS: bounded page ranges, + and automatic safe division')

        # Angle spinbox, free rotation, preview and retaining original on disk.
        editor = ImageEditor(image)
        editor.angle_spin.setValue(12.5)
        assert editor.angle == 12.5
        editor.set_angle(90)
        assert editor.angle == 90
        assert editor._rotated().size == (140, 260)
        editor.close()
        print('PASS: arbitrary rotation, 90 degrees and visual image canvas')

        # Make sure the physical action button exists for image text and crop.
        wheel = WheelWindow()
        wheel.set_context([str(image)], 'image_single', ['images_pdf','ocr_image_text','visual_image'])
        names = [b.objectName() for b in wheel.action_buttons]
        assert 'wheel_action_ocr_image_text' in names
        assert 'wheel_action_visual_image' in names
        wheel.deleteLater()
        app.processEvents()
        print('PASS: physical Quick Wheel buttons for image OCR and crop')
    print('GUI component tests successful (not a test of Finder permissions).')

if __name__ == '__main__':
    main()
