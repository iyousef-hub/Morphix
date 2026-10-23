from pathlib import Path
import ast

BASE = Path(__file__).resolve().parents[1]

def test_core_compiles():
    for name in ('main.py','quickwheel.py','wheel_preferences.py','branding.py','native_hotkeys.py','app_assets.py'):
        ast.parse((BASE / name).read_text(encoding='utf-8'))

def test_branded_assets_present():
    for name in ('morphix_logo.svg','morphix_logo.png','morphix.ico'):
        assert (BASE / 'assets' / name).stat().st_size > 500

def test_hidden_studio_on_launch():
    text = (BASE / 'main.py').read_text(encoding='utf-8')
    assert 'win.hide()' in text
    assert 'setQuitOnLastWindowClosed(False)' in text

def test_pointer_positioning():
    text = (BASE / 'quickwheel.py').read_text(encoding='utf-8')
    assert 'QCursor.pos()' in text
    assert 'QGuiApplication.screenAt(anchor)' in text and 'place_rect(' in text


def test_wheel_personalization_persisted():
    prefs = (BASE / 'wheel_preferences.py').read_text()
    wheel = (BASE / 'quickwheel.py').read_text()
    for key in ('wheel_size', 'wheel_opacity', 'wheel_accent',
                'wheel_glow', 'wheel_animation', 'hub_shape', 'hub_position', 'hub_visibility'):
        assert f"st.setValue('{key}'" in prefs
        assert f"st.value('{key}'" in wheel
    # v1.4.7 opens Settings in a separate, normal Studio process.
    assert 'from wheel_preferences import WheelSettings' in (BASE / 'studio_host.py').read_text()

def test_shared_live_preview_renderer():
    wheel = (BASE / 'quickwheel.py').read_text()
    prefs = (BASE / 'wheel_preferences.py').read_text()
    assert 'def _render_wheel(' in wheel
    assert '_render_wheel(painter' in wheel
    assert '_render_wheel(p,' in prefs
