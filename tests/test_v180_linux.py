"""v1.8.0: Linux integration (desktop files, clipboard selection, shortcut parsing)."""
import os
import sys

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='Linux only')


def test_desktop_integration_files(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    import linux_integration
    importlib.reload(linux_integration)
    written = linux_integration.install()
    names = {p.name for p in written}
    assert {'morphix.desktop', 'Morphix', 'morphix.nemo_action'} <= names
    script = tmp_path / 'data' / 'nautilus' / 'scripts' / 'Morphix'
    assert os.access(script, os.X_OK) and '--hub' in script.read_text()


def test_uri_list_parsing(tmp_path):
    import linux_integration
    f = tmp_path / 'a b.pdf'
    f.write_bytes(b'%PDF')
    text = 'copy\nfile://' + str(f).replace(' ', '%20') + '\nfile:///does/not/exist.pdf\n'
    assert linux_integration.files_from_uri_text(text) == [str(f)]


def test_shortcut_formats():
    import linux_hotkeys
    assert linux_hotkeys.parse_shortcut('<ctrl>+<shift>+m') == (['<ctrl>', '<shift>'], 'm')
    assert linux_hotkeys.gnome_binding('<ctrl>+<shift>+m') == '<Control><Shift>m'


def test_linux_words():
    import i18n
    assert 'Ctrl + C' in i18n.for_linux('x', 'en', 'Select one or more files in Finder, then try again.')
    assert i18n.for_linux('Show in Finder', 'en') == 'Show in folder'
