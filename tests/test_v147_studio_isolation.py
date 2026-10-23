"""Portable regression tests for the new Studio process architecture."""
import ast
from pathlib import Path
import sys
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio_host import studio_start_args, encode_studio_message, decode_studio_message, studio_socket_name


def test_frozen_and_source_studio_launch():
    assert studio_start_args('/x/python', '/app/main.py') == ['/x/python','/app/main.py','--studio-window']
    assert studio_start_args('/x/Morphix', '/app/main.py', frozen=True) == ['/x/Morphix','--studio-window']


def test_start_args_preserves_selected_paths():
    paths=['/tmp/عربي doc.pdf', '/tmp/photo number 1.png']
    args=studio_start_args('/x/python','/app/main.py',paths=paths,command='preferences',page=2)
    assert json.loads(args[args.index('--initial-paths')+1]) == paths
    assert args[-2:] == ['--studio-preferences','2']


def test_ipc_supports_navigation_and_filters_missing_files(tmp_path):
    f=tmp_path/'sample image.png'
    f.write_bytes(b'hello')
    command,page,paths=decode_studio_message(encode_studio_message([f,tmp_path/'does-not-exist'],command='preferences',page=2))
    assert command == 'preferences' and page == 2 and paths == [str(f)]


def test_rejects_invalid_ipc_data():
    for data in (b'not json', b'{}', b'{"command":"rm -rf", "paths":[]}',
                 b'{"command":"raise", "paths":"bad"}',
                 b'{"command":"raise", "page":99}'):
        with pytest.raises((ValueError,UnicodeDecodeError)):
            decode_studio_message(data)


def test_studio_no_longer_switches_dock_policy_in_same_process():
    main=(ROOT/'main.py').read_text()
    wheel=(ROOT/'quickwheel.py').read_text()
    assert "if '--studio-window' in sys.argv" in main
    assert 'self.wheel.hide()' in wheel[wheel.index('def open_studio('):wheel.index('def on_studio_hidden(')]
    assert 'set_studio_visible(True)' not in wheel
    assert 'installEventFilter(self)' not in main
    assert "self.files.quick_actions_requested.connect(self.show_actions)" in main
    ast.parse((ROOT/'studio_host.py').read_text())
