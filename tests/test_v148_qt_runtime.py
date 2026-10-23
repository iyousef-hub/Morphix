"""Regression coverage for Qt Cocoa absence and detached Studio diagnostics.

The Linux CI runner does not have macOS Cocoa; these tests verify the
platform-independent safety logic, not real Mac windowing.
"""
import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qt_macos_runtime import cocoa_plugin_path, clean_qt_environment
from studio_host import studio_start_args, start_studio_process


def test_cocoa_guard_detects_missing_and_present(tmp_path):
    expected = tmp_path / 'Qt' / 'plugins' / 'platforms' / 'libqcocoa.dylib'
    assert cocoa_plugin_path(tmp_path) == expected
    assert not expected.exists()
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b'fake fixture, never loaded')
    assert cocoa_plugin_path(tmp_path).is_file()


def test_clean_launch_environment():
    cleaned = clean_qt_environment({'QT_PLUGIN_PATH': '/anaconda/qt',
                                    'QT_QPA_PLATFORM_PLUGIN_PATH': '/old-qt',
                                    'PYTHONPATH': '/some/legacy/library',
                                    'DYLD_LIBRARY_PATH': '/other/qt',
                                    'HOME': '/Users/test', 'SAFE_VAR': 'yes'})
    for name in ('QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','PYTHONPATH','DYLD_LIBRARY_PATH'):
        assert name not in cleaned
    assert cleaned['SAFE_VAR'] == 'yes'
    assert cleaned['HOME'] == '/Users/test'


def test_studio_logs_failure_and_preserves_args(tmp_path, monkeypatch):
    import studio_host
    calls = {}
    class FakeProcess:
        pid = 123
    def fake_popen(args, **kwargs):
        calls['args'], calls['kwargs'] = args, kwargs
        return FakeProcess()
    monkeypatch.setattr(studio_host.subprocess if hasattr(studio_host,'subprocess') else __import__('subprocess'), 'Popen', fake_popen)
    monkeypatch.setenv('QT_PLUGIN_PATH','/conda/plugins')
    monkeypatch.setenv('QT_QPA_PLATFORM_PLUGIN_PATH','/old/plugins')
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    proc = start_studio_process('/usr/bin/python3',tmp_path/'main.py', paths=['/x/photo.png'])
    assert proc.pid == 123
    assert calls['args'][:3] == ['/usr/bin/python3',str(tmp_path/'main.py'),'--studio-window']
    assert calls['kwargs']['env'].get('QT_PLUGIN_PATH') is None
    assert calls['kwargs']['env'].get('QT_QPA_PLATFORM_PLUGIN_PATH') is None
    assert (tmp_path/'.local'/'state'/'morphix'/'studio.log').exists() or (tmp_path/'Library'/'Logs'/'Morphix'/'studio.log').exists()


def test_mac_launcher_checks_cocoa_before_start():
    script = (ROOT/'Launch_Morphix_Mac.command').read_text()
    assert 'doctor_qt_macos.py' in script
    assert 'qt_preflight.log' in script
    main = (ROOT/'main.py').read_text()
    assert 'configure_qt_macos()' in main
    wheel = (ROOT/'quickwheel.py').read_text()
    assert '_check_studio_launch' in wheel
