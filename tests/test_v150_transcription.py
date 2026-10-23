"""Speech → Text pipeline tests. A fake backend replaces the Whisper model so the
chunking, resume, timestamps and output formats are tested without weights."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import transcription_engine as te  # noqa: E402


def make_audio(path, pattern, video=False):
    """pattern: list of (kind, seconds) with kind 'tone' or 'silence'."""
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    inputs, labels = [], []
    for i, (kind, secs) in enumerate(pattern):
        src = (f'sine=frequency=440:sample_rate=16000:duration={secs}' if kind == 'tone'
               else f'anullsrc=r=16000:cl=mono:d={secs}')
        inputs += ['-f', 'lavfi', '-i', src]
        labels.append(f'[{i}:a]')
    cmd = [ff, '-hide_banner', '-loglevel', 'error', '-y', *inputs]
    if video:
        total = sum(s for _, s in pattern)
        cmd += ['-f', 'lavfi', '-i', f'color=c=blue:s=64x64:r=5:d={total}']
    filt = ''.join(labels) + f'concat=n={len(pattern)}:v=0:a=1[a]'
    cmd += ['-filter_complex', filt, '-map', '[a]']
    if video:
        cmd += ['-map', f'{len(pattern)}:v', '-c:v', 'libx264', '-preset', 'ultrafast']
    cmd += ['-ac', '1', str(path)]
    subprocess.run(cmd, check=True)


class FakeBackend:
    """Emits one segment per 1s+ tone burst found by simple energy detection."""
    instances = 0

    def __init__(self, quality, fail_after_chunks=None):
        FakeBackend.instances += 1
        self.calls = 0
        self.fail_after = fail_after_chunks

    def detect(self, audio):
        return 'ar'

    def transcribe(self, audio, language, prompt=None):
        import numpy as np
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise KeyboardInterrupt('simulated cancel')
        win = te.SAMPLE_RATE // 10
        energy = np.abs(audio[: len(audio) // win * win]).reshape(-1, win).mean(axis=1) > 0.02
        start = None
        for i, on in enumerate(list(energy) + [False]):
            if on and start is None:
                start = i
            elif not on and start is not None:
                yield start / 10, i / 10, f'مرحبا {language} {start}'
                start = None


def test_plan_chunks_cuts_in_silence():
    chunks = te.plan_chunks(3600, [590.0, 1205.5, 1790.0, 2400.0, 3010.0], chunk=600, search=75)
    assert chunks[0] == (0.0, 590.0)
    assert chunks[1][0] == 590.0 and chunks[1][1] == 1205.5
    assert chunks[-1][1] == 3600.0
    assert all(b > a for a, b in chunks)
    # contiguous, no gaps / overlaps
    assert all(chunks[i][1] == chunks[i + 1][0] for i in range(len(chunks) - 1))


def test_plan_chunks_short_file_single_chunk():
    assert te.plan_chunks(300, []) == [(0.0, 300.0)]


def test_plan_chunks_without_silence_falls_back_to_fixed():
    chunks = te.plan_chunks(5 * 3600, [], chunk=600)
    assert len(chunks) == 30
    assert chunks[-1][1] == 5 * 3600


def test_formats():
    segs = [{'start': 0.5, 'end': 2.25, 'text': 'السلام عليكم'},
            {'start': 3661.0, 'end': 3662.5, 'text': 'Hello'}]
    srt = te.to_srt(segs)
    assert '00:00:00,500 --> 00:00:02,250' in srt and '01:01:01,000' in srt
    assert te.to_vtt(segs).startswith('WEBVTT')
    assert '[1:01:01] Hello' in te.to_txt(segs, timestamps=True)
    assert 'السلام عليكم' in te.to_txt(segs)


@pytest.mark.parametrize('video', [False, True])
def test_end_to_end_with_offsets(tmp_path, video):
    src = tmp_path / ('talk.mp4' if video else 'talk.m4a')
    make_audio(src, [('silence', 2), ('tone', 3), ('silence', 4), ('tone', 2), ('silence', 3),
                     ('tone', 2), ('silence', 2)], video=video)
    messages, values = [], []
    out = te.transcribe_media([str(src)], tmp_path / 'out', values.append, language='auto',
                              formats=['txt', 'srt', 'txt_ts'], status=messages.append,
                              backend_factory=FakeBackend, chunk_seconds=6)
    names = sorted(p.name for p in out)
    assert names == ['talk_transcript.srt', 'talk_transcript.txt', 'talk_transcript_timestamps.txt']
    srt = (tmp_path / 'out' / 'talk_transcript.srt').read_text(encoding='utf-8')
    # Three tone bursts across several chunks -> three cues at absolute times.
    assert srt.count('-->') == 3
    assert '00:00:02' in srt and '00:00:09' in srt and '00:00:14' in srt
    assert 'مرحبا ar' in srt
    assert values[-1] == 100 and values == sorted(values)
    # checkpoint + partial removed on success
    assert not list((tmp_path / 'out').glob('.*morphix-transcript*'))
    assert not list((tmp_path / 'out').glob('*.partial.txt'))


def test_resume_after_interruption(tmp_path):
    src = tmp_path / 'lecture.wav'
    make_audio(src, [('tone', 2), ('silence', 4)] * 6)          # 36 s
    out_dir = tmp_path / 'out'

    with pytest.raises(KeyboardInterrupt):
        te.transcribe_media([str(src)], out_dir, chunk_seconds=6, formats=['srt'],
                            backend_factory=lambda q: FakeBackend(q, fail_after_chunks=2))
    cp = te.checkpoint_path(out_dir, src)
    state = json.loads(cp.read_text(encoding='utf-8'))
    assert len(state['done']) == 2
    assert (out_dir / 'lecture_transcript.partial.txt').is_file()

    calls = []

    class Counting(FakeBackend):
        def transcribe(self, audio, language, prompt=None):
            calls.append(prompt)
            yield from super().transcribe(audio, language, prompt)

    out = te.transcribe_media([str(src)], out_dir, chunk_seconds=6, formats=['srt'],
                              backend_factory=Counting)
    total = len(state['chunks'])
    assert len(calls) == total - 2           # finished parts were not redone
    assert out[0].read_text(encoding='utf-8').count('-->') == 6
    assert not cp.exists()


def test_no_audio_track_is_clear_error(tmp_path):
    import imageio_ffmpeg
    v = tmp_path / 'silent_video.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-loglevel', 'error', '-y', '-f', 'lavfi',
                    '-i', 'color=c=red:s=64x64:d=2', '-c:v', 'libx264', '-preset', 'ultrafast',
                    str(v)], check=True)
    with pytest.raises(ValueError, match='No audio track'):
        te.transcribe_media([str(v)], tmp_path, backend_factory=FakeBackend)


def test_missing_model_message(tmp_path, monkeypatch):
    monkeypatch.setenv('MORPHIX_MODELS', str(tmp_path / 'none'))
    monkeypatch.setattr(te, '_bundled_roots', lambda: iter(()))
    assert te.model_dir('fast') is None
    src = tmp_path / 'x.mp3'
    src.write_bytes(b'0')
    if te.engine_available():
        with pytest.raises(RuntimeError, match='not downloaded yet'):
            te.transcribe_media([str(src)], tmp_path, quality='fast')
    if te.engine_available():
        with pytest.raises(RuntimeError, match='not downloaded yet'):
            te.WhisperBackend('fast')


def test_actions_offered_for_audio_and_video(tmp_path):
    import ast
    tree = ast.parse((ROOT / 'main.py').read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'supported_actions')
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'sa', 'exec'), ns)
    for name in ('a.mp4', 'b.mov', 'c.mp3', 'd.wav', 'e.m4a', 'f.m4b', 'g.opus'):
        p = tmp_path / name
        p.write_bytes(b'\0' * 32)
        assert 'transcribe_media' in ns['supported_actions']([str(p)]), name


def test_engine_core_dispatch(tmp_path, monkeypatch):
    import engine_core
    called = {}

    def fake(paths, out_dir, progress=None, **kw):
        called.update(kw)
        return [Path(out_dir) / 'x.txt']
    monkeypatch.setattr(te, 'transcribe_media', fake)

    class P:
        def emit(self, v): pass
        def status(self, t): pass
    out = engine_core.execute('transcribe_media', ['a.mp3'], str(tmp_path), P(),
                              {'language': 'en', 'quality': 'fast', 'formats': ['srt']})
    assert out and called['language'] == 'en' and called['quality'] == 'fast'
    assert called['status'] is not None


def test_context_prompt_carries_previous_part(tmp_path):
    src = tmp_path / 'ctx.wav'
    make_audio(src, [('tone', 2), ('silence', 4)] * 3)
    prompts = []

    class Spy(FakeBackend):
        def transcribe(self, audio, language, prompt=None):
            prompts.append(prompt)
            yield from super().transcribe(audio, language, prompt)
    te.transcribe_media([str(src)], tmp_path / 'o', chunk_seconds=6, formats=['txt'],
                        language='ar', backend_factory=Spy)
    assert prompts[0].startswith(te.STYLE_PROMPTS['ar'])
    assert 'مرحبا' in prompts[1]          # text of part 1 is context for part 2
