"""v1.7.1: Office → PDF fixes (Windows silent failure, speed, Microsoft Office)."""
import sys

import ms_office
import office_engine


def test_svp_plugin_is_not_forced_on_windows(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('SAL_USE_VCLPLUGIN', 'svp')
    assert 'SAL_USE_VCLPLUGIN' not in office_engine._office_env()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert office_engine._office_env()['SAL_USE_VCLPLUGIN'] == 'svp'


def test_empty_failure_still_explains():
    class Done:
        returncode, stdout, stderr = 1, '', ''
    assert 'exit code 1' in office_engine._failure_details(Done())


def test_profile_lock_allows_one_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(office_engine, '_profile_root', lambda: tmp_path / 'office_profile')
    with office_engine._ProfileLock() as first:
        assert first == tmp_path / 'office_profile'
        with office_engine._ProfileLock() as second:
            assert second is None  # falls back to a temporary profile
    assert not (tmp_path / 'office_profile.lock').exists()


def test_microsoft_office_only_on_windows(tmp_path):
    assert ms_office.available('.pptx') is False or sys.platform == 'win32'
    assert ms_office.APPS['.pptx'] == 'PowerPoint.Application'
    assert office_engine._try_ms_office(tmp_path / 'a.pptx', tmp_path, 'pdf:calc_pdf_Export') is None
