"""Run manually on macOS/Windows to smoke-test the real Studio and shortcut recorder.

  .venv/bin/python gui_selftest_v146.py

Requires an active desktop; do not run on a headless CI server.
"""
import sys
from PySide6.QtCore import Qt, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from main import Window
from shortcut_recorder import ShortcutRecorder
from wheel_preferences import WheelSettings

app = QApplication.instance() or QApplication(sys.argv)
recorder = ShortcutRecorder('<cmd>+<shift>+m')
recorder.show()
QTest.qWaitForWindowExposed(recorder)
recorder.start_recording()
QTest.keyPress(recorder, Qt.Key_Delete, Qt.ControlModifier | Qt.ShiftModifier)
assert recorder.shortcut() == '<ctrl>+<shift>+<delete>', recorder.shortcut()
recorder.close()

studio = Window()
studio.show()
app.processEvents()
assert studio.isVisible()
assert studio.files is not None and studio.action_box is not None
assert studio.hero_shortcut.text().startswith('Select files')
studio.close()

settings = WheelSettings(QSettings('Morphix','Morphix'))
settings.show()
app.processEvents()
assert settings.pages.count() == 5
assert settings.shortcut_edit.shortcut()
assert settings.login_checkbox is not None
settings.reject()
print('Morphix v1.4.6 GUI smoke test: PASS', flush=True)
