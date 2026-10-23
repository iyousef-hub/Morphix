"""Run on macOS: python gui_selftest_v143.py

This opens the actual wheel and exercises the immediate mouse-press handler.
It is a non-destructive test with a temporary image, not a replacement for
clicking the floating wheel with a physical mouse.
"""
from pathlib import Path
import tempfile
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PIL import Image
from quickwheel import WheelWindow


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='morphix_v143_') as td:
        source = Path(td) / 'image.png'
        Image.new('RGB', (20, 20), '#328bd9').save(source)
        wheel = WheelWindow()
        wheel.set_context([str(source)], 'image_single', ['images_pdf', 'image_jpg', 'image_compress'])
        wheel.display()
        app.processEvents()
        assert wheel.isVisible(), 'The Quick Wheel failed to show'
        assert len(wheel.action_buttons) == 3
        first = wheel.action_buttons[0]
        assert first.isVisible(), 'The transparent Make PDF hit target is hidden'
        events = []
        wheel.action_requested.connect(events.append)
        QTest.mousePress(first, Qt.LeftButton, pos=first.rect().center())
        app.processEvents()
        assert events == ['images_pdf'], f'Make PDF press was not dispatched: {events}'
        assert not wheel.isVisible(), 'Wheel should hide immediately after selection'
        print('PASS: Make PDF activates on mouse press and hides wheel')
        wheel.set_context([str(source)], 'image_single', ['images_pdf', 'image_jpg', 'image_compress'])
        wheel.display()
        app.processEvents()
        first = wheel.action_buttons[0]
        assert first.isVisible()
        assert wheel.width() == wheel.height()
        wheel.hide()
        wheel.deleteLater()
        app.processEvents()
        print('PASS: transparent actions are retained on identical selections')

if __name__ == '__main__':
    main()
