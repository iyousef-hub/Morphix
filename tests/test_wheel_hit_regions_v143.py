"""Regression checks for the invisible hit areas in Morphix v1.4.3.

Native event delivery still requires live macOS testing; these checks
validate the source architecture without a Qt runtime in the build host.
"""
import ast
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'quickwheel.py').read_text()
TREE = ast.parse(SOURCE)


def method_source(classname, method):
    cls = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == classname)
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method)
    return ast.get_source_segment(SOURCE, fn)


def test_toolbutton_has_no_native_rectangular_paint():
    method = method_source('WheelActionButton', 'paintEvent')
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'paintEvent' for n in ast.walk(ast.parse(method)))
    assert 'event.accept()' in method
    assert 'WA_NoSystemBackground' in SOURCE
    assert "draw_controls=True" in method_source('WheelWindow', 'paintEvent')


def test_mouse_press_dispatches_without_requiring_release():
    method = method_source('WheelActionButton', 'mousePressEvent')
    assert 'self.wheel.invoke_action(' in method
    assert 'event.button() == Qt.LeftButton' in method
    invoke = method_source('WheelWindow', 'invoke_action')
    assert 'self.hide()' in invoke
    assert 'QTimer.singleShot(0,' in invoke


def test_context_does_not_recreate_widgets_when_selection_only_changes():
    method = method_source('WheelWindow', 'set_context')
    assert 'if next_actions != self.actions:' in method
    assert 'self.rebuild_buttons()' in method


def test_options_still_include_image_pdf():
    assert "'images_pdf': ('Make PDF','pdf')" in SOURCE
