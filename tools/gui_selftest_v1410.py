"""macOS GUI smoke test for v1.4.10: use on the Mac, not headless Linux.

Run from Morphix 22: .venv_clean/bin/python gui_selftest_v1410.py
Tests a real Qt widget creation and the standalone Studio click pathways.
Does not require the background Morphix helper to be running and does not
persist changes to the real user's keyboard shortcut.
"""
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtTest import QTest
from main import Window
from studio_host import StudioController
from wheel_preferences import WheelSettings
from shortcut_recorder import ShortcutRecorder

app = QApplication.instance() or QApplication(sys.argv)

# The constructor previously raised AttributeError from event() triggered by
# QLineEdit.setReadOnly(True) and blocked ALL Preferences pages.
rec = ShortcutRecorder('<cmd>+<shift>+m')
assert rec.shortcut() == '<cmd>+<shift>+m'
rec.show()
app.processEvents()
rec.close()

with tempfile.TemporaryDirectory(prefix='morphix-gui-test-') as td:
    settings = QSettings(str(Path(td) / 'prefs.ini'), QSettings.IniFormat)
    prefs = WheelSettings(settings)
    assert prefs.pages.count() == 5
    assert prefs.shortcut_edit.shortcut()
    prefs._switch_page(2)
    assert prefs.pages.currentIndex() == 2
    prefs.close()

window = Window()
window.controller = StudioController(window)
background_calls = []
window.controller.notify_background = lambda command: background_calls.append(command) or True
window.showNormal()
app.processEvents()

# Direct API and actual navigation click should go through IPC controller,
# not call nonexistent StudioController.show_wheel().
window.open_quick_wheel()
assert background_calls == ['wheel'], background_calls
wheel_button = next(btn for btn in window.findChildren(QPushButton) if btn.text().strip().endswith('Quick Wheel'))
QTest.mouseClick(wheel_button, Qt.LeftButton)
app.processEvents()
assert background_calls == ['wheel', 'wheel'], background_calls

# Don't open blocking modal dialogues in the smoke test, but do verify routing.
preferences_calls = []
window.controller.open_preferences = lambda page=0: preferences_calls.append(page)
for button_text, expected in [('Wheel appearance', 0), ('Record a shortcut', 2), ('Customize Wheel', 0)]:
    button = next(btn for btn in window.findChildren(QPushButton) if button_text in btn.text())
    QTest.mouseClick(button, Qt.LeftButton)
    app.processEvents()
    assert preferences_calls[-1] == expected, (button_text, preferences_calls)

print('MORPHIX 1.4.10 GUI SHORTCUT + STUDIO BUTTONS: PASS', flush=True)
window.close()
