"""Regression tests for real user traceback in macOS Studio v1.4.9.

Qt can synchronously dispatch QWidget events during initialization.  The
recorder used to read _recording before setting it.  The other failure was a
misnamed method call from standalone Studio into its IPC-only controller.
"""
import ast
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_studio_wheel_callback_routes_through_studio_controller():
    """Execute the real Window callback without importing the whole Qt GUI."""
    tree = ast.parse((ROOT / 'main.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'open_quick_wheel')
    compiled = compile(ast.Module(body=[method], type_ignores=[]), str(ROOT / 'main.py'), 'exec')
    namespace = {}
    exec(compiled, namespace)
    calls = []
    controller = types.SimpleNamespace(open_quick_wheel=lambda: calls.append('wheel'))
    standalone = types.SimpleNamespace(controller=controller)
    namespace['open_quick_wheel'](standalone)
    assert calls == ['wheel']


def test_shortcut_recorder_handles_events_during_constructor(monkeypatch):
    """Fake QLineEdit fires events in __init__ AND setReadOnly like Qt may do."""
    sys.path.insert(0, str(ROOT))
    class FakeQt:
        StrongFocus = 2
        PointingHandCursor = 3
        AlignCenter = 4
        MouseFocusReason = 5
        KeyPress = 6
        Key_Tab = 0x01000001
        Key_Backtab = 0x01000002
        Key_Control = 0x01000021
        Key_Shift = 0x01000020
        Key_Alt = 0x01000023
        Key_Meta = 0x01000022
        Key_Escape = 0x01000000
        Key_A = 65
        Key_Z = 90
        Key_0 = 48
        Key_9 = 57
        Key_F1 = 0x01000030
        Key_F20 = Key_F1+19
        ControlModifier = 1
        ShiftModifier = 2
        AltModifier = 4
        MetaModifier = 8
        Key_Delete = 0x01000007
        Key_Backspace = 0x01000003
        Key_Space = 0x20
        Key_Return = 0x01000004
        Key_Enter = 0x01000005
        Key_Up = 0x01000013
        Key_Down = 0x01000015
        Key_Left = 0x01000012
        Key_Right = 0x01000014
        Key_Home = 0x01000010
        Key_End = 0x01000011
        Key_PageUp = 0x01000016
        Key_PageDown = 0x01000017
        Key_Insert = 0x01000006

    class FakeEvent:
        def type(self): return 0

    class FakeLineEdit:
        def __init__(self, parent=None):
            self.event(FakeEvent())  # Qt may dispatch a lifecycle event already.
        def event(self, event):
            return False
        def setReadOnly(self, val):
            self.event(FakeEvent())  # Real reported traceback occurred here.
        def __getattr__(self, name):
            if name in ('setObjectName', 'setFocusPolicy', 'setCursor', 'setMinimumHeight',
                        'setAlignment', 'setToolTip', 'setText', 'setProperty', 'setFocus',
                        'clearFocus'):
                return lambda *args, **kwargs: None
            raise AttributeError(name)

    fake_pkg = types.ModuleType('PySide6')
    fake_core = types.ModuleType('PySide6.QtCore')
    fake_widgets = types.ModuleType('PySide6.QtWidgets')
    fake_core.Qt = FakeQt
    fake_core.Signal = lambda *args: types.SimpleNamespace(emit=lambda *_: None)
    fake_core.QEvent = types.SimpleNamespace(KeyPress=FakeQt.KeyPress)
    fake_widgets.QLineEdit = FakeLineEdit
    monkeypatch.setitem(sys.modules, 'PySide6', fake_pkg)
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', fake_core)
    monkeypatch.setitem(sys.modules, 'PySide6.QtWidgets', fake_widgets)
    monkeypatch.setattr(sys, 'platform', 'linux')
    spec = importlib.util.spec_from_file_location('test_shortcut_recorder_v1410', ROOT / 'shortcut_recorder.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    widget = mod.ShortcutRecorder('<ctrl>+<shift>+m')
    assert widget._recording is False
    assert widget.shortcut() == '<ctrl>+<shift>+m'
    # Constructor behavior was tested, including native-like early events.
