"""v1.4.9 regression: don't downgrade from working Homebrew venv to Anaconda venv."""
import os
import sys
import types
from pathlib import Path
from unittest import mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runtime_guard
import qt_macos_runtime


def _fake_python(dir):
    p = dir / 'bin' / 'python'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('placeholder')
    return p


def test_selected_clean_venv_is_never_reexecuted_into_old_venv(tmp_path, monkeypatch):
    _fake_python(tmp_path/'.venv')
    _fake_python(tmp_path/'.venv_clean')
    monkeypatch.setattr(runtime_guard.sys, 'prefix', str(tmp_path/'.venv_clean'))
    monkeypatch.setattr(runtime_guard, 'missing_modules', lambda: [])
    with mock.patch.object(runtime_guard.os, 'execv') as call:
        runtime_guard.verify_or_relaunch(tmp_path)
    call.assert_not_called()


def test_explicit_legacy_env_is_not_overridden_either(tmp_path, monkeypatch):
    _fake_python(tmp_path/'.venv')
    _fake_python(tmp_path/'.venv_clean')
    monkeypatch.setattr(runtime_guard.sys, 'prefix', str(tmp_path/'.venv'))
    monkeypatch.setattr(runtime_guard, 'missing_modules', lambda: [])
    with mock.patch.object(runtime_guard.os, 'execv') as call:
        runtime_guard.verify_or_relaunch(tmp_path)
    call.assert_not_called()


def test_from_outside_prefers_clean_env(tmp_path, monkeypatch):
    _fake_python(tmp_path/'.venv')
    clean = _fake_python(tmp_path/'.venv_clean')
    monkeypatch.setattr(runtime_guard.sys, 'prefix', '/opt/anaconda3')
    monkeypatch.setattr(runtime_guard, 'missing_modules', lambda: [])
    with mock.patch.object(runtime_guard.os, 'execv') as call:
        runtime_guard.verify_or_relaunch(tmp_path)
    call.assert_called_once()
    assert call.call_args.args[0] == str(clean)


def test_missing_clean_falls_back_to_existing_venv(tmp_path):
    old = _fake_python(tmp_path/'.venv')
    assert runtime_guard.preferred_project_python(tmp_path) == old


def test_qt_hidden_repair_targets_only_qt_dir_and_only_hidden(monkeypatch, tmp_path):
    plat = tmp_path/'Qt'/'plugins'/'platforms'
    plat.mkdir(parents=True)
    (plat/'libqcocoa.dylib').write_bytes(b'cocoa')
    (plat/'libqoffscreen.dylib').write_bytes(b'offscreen')
    other = tmp_path/'outside.dylib'
    other.write_bytes(b'not in Qt folder')
    monkeypatch.setattr(qt_macos_runtime.sys, 'platform', 'darwin')
    monkeypatch.setattr(qt_macos_runtime.stat, 'UF_HIDDEN', 32768, raising=False)
    orig_stat = Path.stat
    def fake_stat(self, *args, **kwargs):
        original = orig_stat(self, *args, **kwargs)
        value = 32768 if self.name == 'libqcocoa.dylib' else 0
        return types.SimpleNamespace(st_flags=value, st_mode=original.st_mode, st_dev=original.st_dev, st_ino=original.st_ino)
    monkeypatch.setattr(Path, 'stat', fake_stat)
    changed = []
    monkeypatch.setattr(qt_macos_runtime.os, 'chflags', lambda p, flags: changed.append((Path(p), flags)), raising=False)
    found = qt_macos_runtime.restore_hidden_qt_plugins(tmp_path/'Qt'/'plugins')
    assert found == [plat/'libqcocoa.dylib']
    assert changed == [(plat/'libqcocoa.dylib', 0)]


def test_launcher_prefers_clean_runtime():
    source = (ROOT/'Launch_Morphix_Mac.command').read_text()
    assert 'PY="$ROOT/runtime/bin/python"' in source
    assert 'nohup "\\$PY" "\\$ROOT/main.py"' in source   # inside generated Morphix.app
    main = (ROOT/'main.py').read_text()
    assert 'configure_qt_macos()' in main
