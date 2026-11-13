"""Morphix 1.11: video/audio compression, the tools library and “show all tools”."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import media_compress as mc


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@pytest.fixture(scope='module')
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp('media')
    video = d / 'clip.mov'
    subprocess.run([_ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
                    'testsrc2=size=1280x720:rate=30:duration=6', '-f', 'lavfi', '-i', 'sine=frequency=330:duration=6',
                    '-vf', 'noise=alls=10:allf=t', '-c:v', 'libx264', '-crf', '12', '-preset', 'ultrafast',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', str(video)], check=True)
    audio = d / 'talk.wav'
    subprocess.run([_ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=40',
                    str(audio)], check=True)
    return video, audio


def test_probe_reads_video_and_audio(media):
    video, audio = media
    v = mc.probe(video)
    assert v['video'] and v['audio'] and (v['width'], v['height']) == (1280, 720)
    assert 5.5 < v['duration'] < 6.5
    a = mc.probe(audio)
    assert a['audio'] and not a['video']


def test_quality_drops_as_strength_rises(media):
    info = mc.probe(media[0])
    levels = [mc.plan(info, 'strength', s)['level'] for s in (0, 50, 100)]
    sizes = [mc.plan(info, 'strength', s)['est'] for s in (0, 50, 100)]
    assert levels[0] >= levels[1] >= levels[2]
    assert sizes[0] > sizes[1] > sizes[2]


def test_tiny_target_warns_quality_is_lost():
    info = {'name': 'long.mp4', 'size': 2_000 * mc.MB, 'duration': 3600.0, 'video': True, 'audio': True,
            'width': 1920, 'height': 1080, 'fps': 30.0, 'bitrate': 4500}
    p = mc.plan(info, 'target', target_mb=25)
    assert p['ok'] and p['level'] <= 1
    big = mc.plan(info, 'target', target_mb=1500)
    assert big['level'] >= 3
    impossible = mc.plan(info, 'target', target_mb=0.2)
    assert not impossible['ok']


def test_target_size_is_respected(media, tmp_path):
    video, audio = media
    out = mc.compress([video, audio], tmp_path, mode='target', target_mb=0.6)
    assert len(out) == 2
    for f in out:
        assert f.stat().st_size <= 0.6 * mc.MB, f
    assert out[0].suffix == '.mp4' and out[1].suffix == '.m4a'


def test_already_small_file_is_kept_as_is(media, tmp_path):
    audio = media[1]
    out = mc.compress([audio], tmp_path, mode='target', target_mb=500)
    assert out[0].read_bytes() == Path(audio).read_bytes()


def test_recommended_shrinks_heavy_video(media, tmp_path):
    out = mc.compress([media[0]], tmp_path, mode='recommended')
    assert out[0].stat().st_size < Path(media[0]).stat().st_size * 0.7


def test_hub_actions_normal_and_show_all():
    from quickwheel import hub_actions
    supported = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    normal = hub_actions(['c', 'a', 'b', 'd', 'e', 'f', 'g'], supported, 'pdf_single', 6)
    assert normal == ['c', 'a', 'b', 'd', 'e', 'more_actions']
    every = hub_actions(['c', 'a'], supported, 'pdf_single', 6, show_all=True)
    assert every[:2] == ['c', 'a'] and set(every[:-1]) == set(supported) and every[-1] == 'more_actions'
    assert 'more_actions' not in hub_actions(['zip_files'], ['zip_files'], 'mixed', 6)


def test_wheel_uses_two_rings_for_many_tools():
    from quickwheel import wheel_slots, wheel_size_factor
    slots, _ = wheel_slots(6)
    assert {s['ring'] for s in slots} == {0}
    slots, _ = wheel_slots(19)
    assert {s['ring'] for s in slots} == {0, 1} and len(slots) == 19
    assert wheel_size_factor(19) > 1


def test_panel_grids_grow():
    from hub_panel import grid_columns
    assert grid_columns('square', 9) == 3
    assert grid_columns('square', 19) == 5
    assert grid_columns('bar', 19) == 10
    assert grid_columns('rectangle', 19) == 7


def test_pin_toggle_keeps_all_tools_last():
    from tools_library import toggle_pin
    pins = toggle_pin(['a', 'more_actions'], 'b')
    assert pins == ['b', 'a', 'more_actions']
    assert toggle_pin(pins, 'a') == ['b', 'more_actions']


def test_compress_is_offered_for_video_and_audio(media):
    from main import supported_actions
    assert 'compress_media' in supported_actions([str(media[0])])
    assert 'compress_media' in supported_actions([str(m) for m in media[1:]])


def test_arabic_for_new_messages():
    from i18n_ar import AR
    for text in list(mc.MESSAGES.values()) + list(mc.AUDIO_MESSAGES.values()) + ['All tools', 'Target size']:
        assert text in AR, text
