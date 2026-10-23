"""Morphix 1.4.1: verifies Qt wheel rebuild and appearance changes.

Run on a Mac with dependencies already installed:
    python gui_selftest_v141.py
This does not prove native compositor behavior across multiple processes.
"""
from pathlib import Path
import tempfile
from PIL import Image
from PySide6.QtWidgets import QApplication
from quickwheel import WheelWindow


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='morphix_v141_') as d:
        image = Path(d) / 'test.png'
        Image.new('RGB', (100, 100), '#158aff').save(image)
        wheel = WheelWindow()
        wheel.set_context([str(image)], 'image_single', ['images_pdf', 'image_jpg', 'image_compress'])
        wheel.display()
        app.processEvents()
        assert wheel.isVisible()
        for width, accent, opacity in [(220, '#259FFF', 35), (440, '#005EFF', 85), (290, '#3896FF', 78)]:
            wheel.set_appearance(size=width, opacity=opacity, accent=accent)
            app.processEvents()
            assert wheel.isVisible(), 'Wheel did not reappear after resize'
            assert (wheel.width(), wheel.height()) == (width, width)
            assert len(wheel.action_buttons) == 3
            print(f'PASS: wheel repaint {width}px {accent} {opacity}%')
        wheel.hide()
        wheel.deleteLater()
        app.processEvents()
    print('GUI smoke checks passed. Verify on-screen wheel has no ghost on macOS.')


if __name__ == '__main__':
    main()
