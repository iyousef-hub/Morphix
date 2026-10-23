"""On a Mac with the project's .venv active: python gui_selftest_v144.py

Non-destructive GUI smoke test: verifies a REAL QuickImageEditor saves an
edited copy, and a REAL wheel button forwards the click on its own widget.
"""
from pathlib import Path
import tempfile
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from visual_editor import QuickImageEditor
from quickwheel import WheelWindow


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='morphix-144-gui-') as directory:
        sample = Path(directory) / 'sample.png'
        Image.new('RGB', (640, 420), '#317bcd').save(sample)
        editor = QuickImageEditor(str(sample))
        assert editor.windowTitle().startswith('Morphix · Quick Crop'), 'wrong image editor'
        assert editor.canvas.normalized_crop() == (0.0, 0.0, 1.0, 1.0)
        editor.set_angle(17)
        editor.canvas.set_crop_normalized((.2, .2, .8, .8))
        editor.save_copy()
        edited = sample.with_name('sample_edited.png')
        assert edited.exists(), 'Save Copy failed'
        assert Image.open(sample).size == (640, 420), 'original was altered'
        assert Image.open(edited).size != (640, 420), 'rotate+crop did not change output geometry'
        print('PASS: quick crop/rotate saved independent edited image')

        wheel = WheelWindow()
        wheel.set_context([str(sample)], 'image_single', ['visual_image', 'images_pdf', 'image_compress'])
        wheel.display()
        app.processEvents()
        events = []
        wheel.action_requested.connect(events.append)
        QTest.mousePress(wheel.action_buttons[0], Qt.LeftButton,
                         pos=wheel.action_buttons[0].rect().center())
        app.processEvents()
        assert events == ['visual_image'], f'quick-wheel button did not dispatch: {events}'
        assert not wheel.isVisible(), 'wheel remained visible after clicking'
        print('PASS: quick wheel Crop & rotate button responds and hides wheel')
        wheel.close()
    print('Morphix 1.4.4 GUI smoke test: PASS')


if __name__ == '__main__':
    main()
