"""Mac native-wheel click smoke test for Morphix 1.4.11.

Run in a clean environment after closing other Morphix processes:
    .venv_clean/bin/python gui_selftest_v1411.py

A real 3-slice Morphix wheel appears. Click its top sector. The test prints a
CLICK RECEIVED line if the mouse event reached Qt. This exercises the wheel
without Finder Automation permissions, the background shortcut, or conversion.
"""
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from quickwheel import WheelWindow

app = QApplication(sys.argv)
wheel = WheelWindow()
clicked = []
def on_click(action):
    clicked.append(action)
    print('[Morphix GUI test] CLICK RECEIVED:', action, flush=True)
    QTimer.singleShot(0, app.quit)
wheel.action_requested.connect(on_click)
wheel.set_context([], 'image_multi', ['images_pdf', 'image_jpg', 'zip_files'])
wheel.display()
print('Click the TOP slice of the wheel. The terminal should print CLICK RECEIVED.', flush=True)
print('You may close the wheel with Escape. No files are modified.', flush=True)
QTimer.singleShot(15000, app.quit)
app.exec()
assert clicked, 'No mouse click reached the wheel during the test.'
print('MORPHIX 1.4.11 WHEEL MOUSE TEST: PASS', flush=True)
