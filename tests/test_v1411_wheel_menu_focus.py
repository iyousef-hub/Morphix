"""Regression tests for the macOS menu/wheel hang reported in v1.4.10."""
from __future__ import annotations
import ast
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]


def _method(filename, classname, method):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method)


def test_macos_wheel_is_key_capable_toplevel_not_tool_panel():
    code = (ROOT / 'quickwheel.py').read_text(encoding='utf-8')
    assert "surface = Qt.Window if platform.system() == 'Darwin' else Qt.Tool" in code
    assert 'self.activateWindow()' in code
    assert 'activateIgnoringOtherApps_' in code


def test_tray_delays_actions_until_native_menu_closed():
    code = (ROOT / 'quickwheel.py').read_text(encoding='utf-8')
    assert "menu.aboutToShow.connect(lambda: None if self._persistent() else self.hide_wheel())" in code
    assert "self._after_tray_menu(self.open_studio)" in code
    assert "self._after_tray_menu(self.show_wheel)" in code
    assert 'QTimer.singleShot(80, callback)' in code
    assert "if platform.system() == 'Darwin':\n            return" in code


def test_finder_tray_does_not_call_sync_applescript_from_qt_loop():
    fn = _method('quickwheel.py', 'QuickWheelController', 'show_wheel')
    assert isinstance(fn.body[0], ast.If)
    first = ast.unparse(fn.body[0])
    assert "platform.system() == 'Darwin'" in first
    assert "self._read_finder_selection('wheel')" in first
    source = (ROOT / 'quickwheel.py').read_text(encoding='utf-8')
    assert "proc.start('osascript', ['-e', script])" in source
    assert 'timer.start(6500)' in source
    assert 'proc.kill()' in source


def test_async_finder_result_dispatches_paths_without_qt(monkeypatch, tmp_path):
    file_a = tmp_path / 'a.png'
    file_a.write_bytes(b'PNG')
    file_b = tmp_path / 'b.pdf'
    file_b.write_bytes(b'PDF')
    method = _method('quickwheel.py', 'QuickWheelController', '_finder_request_finished')
    namespace={'Path': Path}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(ROOT / 'quickwheel.py'), 'exec'), namespace)
    class FakeProc:
        def exitCode(self): return 0
        def readAllStandardOutput(self): return f'{file_a}\n{file_b}\n{tmp_path}/missing.png\n'.encode()
        def readAllStandardError(self): return b''
    proc=FakeProc()
    got=[]
    self=SimpleNamespace(_finder_request=proc,
            _clear_finder_request=lambda p: 'wheel',
            _display_finder_wheel=lambda paths: got.extend(paths))
    namespace['_finder_request_finished'](self, proc)
    assert got == [str(file_a), str(file_b)]


def test_launch_detects_older_helpers_not_just_current_folder():
    shell=(ROOT / 'Launch_Morphix_Mac.command').read_text(encoding='utf-8')
    assert "pgrep -f" in shell
    assert "Morphix is currently running" in shell
    assert 'Quit it so it can be updated?' in shell
    assert '/opt/homebrew/opt/python@3.13' in shell
    assert 'conda' in shell                                            # Anaconda is skipped
    assert 'PY="$ROOT/runtime/bin/python"' in shell
    assert 'Library/Application Support/Morphix' in shell     # not the protected Desktop


def test_qt_plugin_unhide_precedes_qapplication():
    main=(ROOT / 'main.py').read_text(encoding='utf-8')
    assert main.index('configure_qt_macos()') < main.index('from PySide6.QtWidgets import')
