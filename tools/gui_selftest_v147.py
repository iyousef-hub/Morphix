"""Run on the real desktop to exercise Studio's clickable navigation widgets.

Usage: .venv/bin/python gui_selftest_v147.py
No Finder access, hotkey monitor, or background service required.
"""
import sys
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from main import Window

class StudioProbe(Window):
    def __init__(self):
        self.commands=[]
        super().__init__()
    def open_wheel_settings(self):
        self.commands.append('settings')
    def open_shortcuts(self):
        self.commands.append('shortcuts')
    def open_quick_wheel(self):
        self.commands.append('wheel')

app=QApplication.instance() or QApplication(sys.argv)
win=StudioProbe()
win.showNormal()
app.processEvents()

def click(text, expected):
    btn=next((b for b in win.findChildren(QPushButton) if text in b.text()),None)
    assert btn is not None, f'Button missing: {text}'
    QTest.mouseClick(btn, Qt.LeftButton)
    app.processEvents()
    assert win.commands[-1] == expected, f'No click reached {text}: {win.commands}'

click('Customize Wheel','settings')
click('Wheel appearance','settings')
click('Record a shortcut','shortcuts')
click('Quick Wheel','wheel')
assert win.isVisible()
print('STUDIO QT CLICK TEST: PASS',flush=True)
win.close()
