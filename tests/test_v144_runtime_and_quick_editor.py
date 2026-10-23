"""Morphix v1.4.4 regression tests independent from Qt display availability."""
import ast
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_runtime_guard_fails_early_when_modules_missing(monkeypatch, tmp_path):
    from runtime_guard import verify_or_relaunch
    import runtime_guard
    monkeypatch.setattr(runtime_guard, 'missing_modules', lambda:['PyMuPDF'])
    # No local virtual env available: fail cleanly before instantiating Qt.
    with pytest.raises(SystemExit) as raised:
        verify_or_relaunch(tmp_path)
    assert raised.value.code==2


def test_runtime_guard_distinguishes_symlinked_python(monkeypatch, tmp_path):
    import runtime_guard
    root=tmp_path
    venv=root/'.venv'/'bin'
    venv.mkdir(parents=True)
    (venv/'python').symlink_to(sys.executable)
    monkeypatch.setattr(runtime_guard.sys,'prefix','/opt/anaconda3')
    monkeypatch.setattr(runtime_guard,'missing_modules',lambda:[])
    with mock.patch.object(runtime_guard.os, 'execv') as call:
        runtime_guard.verify_or_relaunch(root)
    assert call.called, 'must switch away from base Python even with same resolved binary'
    exe, args=call.call_args.args
    assert exe==str(venv/'python')
    assert args[1]==str(root/'main.py')


def test_main_checks_runtime_before_importing_qt():
    code=(ROOT/'main.py').read_text()
    assert code.index('verify_or_relaunch(')<code.index('from PySide6.QtCore')
    assert 'import pymupdf as fitz' in (ROOT/'visual_editor.py').read_text()
    assert 'import pymupdf as fitz' in (ROOT/'engine_core.py').read_text()


def test_wheel_opens_quick_editor_directly_without_studio():
    code=(ROOT/'quickwheel.py').read_text()
    module=ast.parse(code)
    cls=next(c for c in module.body if isinstance(c,ast.ClassDef) and c.name=='QuickWheelController')
    fn=next(f for f in cls.body if isinstance(f,ast.FunctionDef) and f.name=='action_selected')
    body=ast.get_source_segment(code,fn)
    assert 'QuickImageEditor(paths[0])' in body
    assert 'editor.exec()' in body
    assert "self.open_studio(self.current_paths or None)" in body  # studio only for explicit action
    assert 'self.studio.start_action(action)' not in body


def test_quick_crop_renders_thumbnail_and_saves_separate_copy():
    code=(ROOT/'visual_editor.py').read_text()
    assert 'self.preview_base.thumbnail((1100, 1100)' in code
    assert 'self._rotated(preview=True)' in code
    assert 'export_image_edit(self.base_image' in code # full-resolution export
    assert "base.stem + '_edited'" in code
    assert 'while candidate.exists()' in code
    assert 'self.scene().addEllipse' in code # visible crop handles


def test_launcher_validates_gui_and_converter_runtime():
    code=(ROOT/'Launch_Morphix_Mac.command').read_text()
    assert 'runtime/bin/python' in code and 'conda' in code  # isolated, never Anaconda
    assert 'import pymupdf' in code
    assert 'PySide6.QtWidgets' in code
    assert 'pip install -r' in code
