"""Offline speech-to-text for audio AND video (Arabic + English).

Built for long recordings (1-5+ hours):

* The audio track is decoded by the bundled FFmpeg in ~10 minute chunks, so
  memory stays flat (about 40 MB of samples at a time) regardless of length.
* Chunk boundaries are moved to the nearest silence, so words are not cut.
* Every finished chunk is written to a checkpoint next to the output. If the
  job is cancelled, the computer sleeps or the app quits, running the same
  action again on the same file resumes where it stopped.
* A readable ``*_transcript.partial.txt`` grows while the job runs.

Engine: faster-whisper (CTranslate2) running locally on the CPU. The speech
model is downloaded ONCE (Studio -> Speech models, or download_speech_models.py)
and afterwards everything runs without internet: transcription always loads
the model with ``local_files_only=True``.

No Qt imports here; the module runs inside the isolated worker process.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SAMPLE_RATE = 16000
CHUNK_SECONDS = 600          # target chunk length
BOUNDARY_SEARCH = 75         # look this far around a target cut for silence
LANGUAGES = ('auto', 'ar', 'en')

# quality key -> (faster-whisper model alias, approx download size, label)
MODELS = {
    'fast': ('small', '≈ 480 MB', 'Fast (small model)'),
    'accurate': ('large-v3-turbo', '≈ 1.6 GB', 'Balanced (large-v3-turbo)'),
    'best': ('large-v3', '≈ 3 GB', 'Most accurate (large-v3)'),
    'max': ('large-v3', '≈ 3 GB', 'Maximum accuracy — slowest (large-v3, full precision)'),
}
# quality -> (compute type, beam size, patience). 'max' uses the same download as
# 'best' but runs it at full precision with a wider search: the highest accuracy
# Whisper can give, at roughly half the speed.
DECODING = {'fast': ('int8', 5, 1.0), 'accurate': ('int8', 5, 1.0),
            'best': ('int8', 5, 1.0), 'max': ('float32', 8, 2.0)}
# Gentle clean-up before recognition: removes rumble and evens out quiet/loud
# speakers (helps lectures, phone recordings and meetings).
CLEAN_FILTER = 'highpass=f=60,dynaudnorm=f=250:g=15:p=0.9:m=8'
DEFAULT_QUALITY = 'best'

# Steers Whisper toward clean, punctuated Modern-Standard spelling instead of
# unpunctuated run-on text (a frequent complaint with Arabic transcripts).
STYLE_PROMPTS = {
    'ar': 'هذا تفريغ نصي دقيق لتسجيل باللغة العربية، مكتوب بإملاء صحيح وعلامات ترقيم واضحة.',
    'en': 'This is an accurate, well-punctuated transcript of an English recording.',
}
CHECKPOINT_VERSION = 2
_LANG = 'en'          # interface language for messages (set per job by the worker)


def _t(text, **fmt):
    try:
        from i18n import trl
        return trl(_LANG, text, **fmt)
    except Exception:
        return text.format(**fmt) if fmt else text


# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

def models_root() -> Path:
    override = os.environ.get('MORPHIX_MODELS')
    if override:
        return Path(override)
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Morphix' / 'models'
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Morphix' / 'models'
    return Path.home() / '.local' / 'share' / 'morphix' / 'models'


def _bundled_roots():
    here = Path(__file__).resolve().parent
    yield here / 'assets' / 'speech_models'
    if getattr(sys, '_MEIPASS', None):
        yield Path(sys._MEIPASS) / 'assets' / 'speech_models'
    if sys.platform == 'darwin':
        yield Path(sys.executable).resolve().parent.parent / 'Resources' / 'assets' / 'speech_models'


def _is_model_dir(path: Path) -> bool:
    return (path / 'model.bin').is_file() and (path / 'config.json').is_file()


def model_dir(quality: str) -> Path | None:
    """Return the local folder of an installed model, or None."""
    if quality not in MODELS:
        raise ValueError(f'Unknown quality: {quality}')
    alias = MODELS[quality][0]
    for root in [*_bundled_roots(), models_root()]:
        candidate = root / alias
        if _is_model_dir(candidate):
            return candidate
    return None


_ENGINE_ERROR = None


def engine_available() -> bool:
    global _ENGINE_ERROR
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception as exc:
        if _ENGINE_ERROR is None:
            _ENGINE_ERROR = f'{type(exc).__name__}: {exc}'
            # Keep the real reason in the log (e.g. a DLL blocked by
            # Windows Smart App Control) instead of only "not installed".
            print(f'[Morphix] Speech engine unavailable: {_ENGINE_ERROR}', flush=True)
        return False


def engine_error():
    return _ENGINE_ERROR


def status() -> dict:
    return {'engine': engine_available(),
            'models': {q: (str(model_dir(q)) if model_dir(q) else None) for q in MODELS}}


def download_model(quality: str, progress=None, status_cb=None, ui_lang='en') -> Path:
    """One-time download (needs internet). Everything after this is offline."""
    global _LANG
    _LANG = ui_lang
    if not engine_available():
        raise RuntimeError(_t('The speech engine is not installed. Run Launch_Morphix_Mac.command once while connected to the internet.'))
    from faster_whisper.utils import download_model as fw_download
    alias = MODELS[quality][0]
    target = models_root() / alias
    target.mkdir(parents=True, exist_ok=True)
    if status_cb:
        status_cb(_t('Downloading the speech model ({size}) — one time only…', size=MODELS[quality][1]))
    if progress:
        progress(3)
    try:
        fw_download(alias, output_dir=str(target))
    except Exception as exc:
        raise RuntimeError(_t('The model could not be downloaded. Please check your internet connection '
                              'and try again.') + f'\n{exc}') from exc
    if not _is_model_dir(target):
        raise RuntimeError(f'Download finished but the model folder is incomplete: {target}')
    if progress:
        progress(100)
    return target


# --------------------------------------------------------------------------
# Audio probing / chunking (FFmpeg only — no extra dependencies)
# --------------------------------------------------------------------------

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _hidden_startupinfo():
    if os.name != 'nt':
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {'startupinfo': si}


_DURATION = re.compile(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)')
_TIME = re.compile(r'time=(\d+):(\d+):(\d+(?:\.\d+)?)')
_SIL_START = re.compile(r'silence_start:\s*(-?\d+(?:\.\d+)?)')
_SIL_END = re.compile(r'silence_end:\s*(-?\d+(?:\.\d+)?)')


def _hms(match) -> float:
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def analyze_audio(path, progress=None):
    """One streaming pass: duration + silence midpoints. Raises if no audio.

    Uses constant memory; on a 5 hour file it takes roughly 1-3 minutes.
    """
    ffmpeg = _ffmpeg()
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-i', str(path), '-vn', '-sn', '-dn',
           '-map', '0:a:0', '-ac', '1', '-ar', '8000',
           '-af', 'silencedetect=noise=-33dB:d=0.35', '-f', 'null', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True, errors='replace', bufsize=1, **_hidden_startupinfo())
    duration = None
    silences = []
    pending_start = None
    tail = []
    has_audio = False
    for line in proc.stderr:
        tail = (tail + [line])[-25:]
        if duration is None and (m := _DURATION.search(line)):
            duration = _hms(m)
        if 'Audio:' in line:
            has_audio = True
        if (m := _SIL_START.search(line)):
            pending_start = max(0.0, float(m.group(1)))
        elif (m := _SIL_END.search(line)) and pending_start is not None:
            silences.append((pending_start + float(m.group(1))) / 2)
            pending_start = None
        elif progress and duration and (m := _TIME.search(line)):
            progress(min(99, int(_hms(m) / duration * 100)))
    proc.wait()
    if proc.returncode != 0 or not has_audio:
        detail = ''.join(tail).strip()
        if 'matches no streams' in detail or not has_audio:
            raise ValueError(_t('No audio track found in {name}', name=Path(path).name))
        raise RuntimeError(_t('Could not read {name}', name=Path(path).name) + f':\n{detail[-800:]}')
    if not duration:
        raise RuntimeError(_t('Could not read {name}', name=Path(path).name))
    return duration, silences


def plan_chunks(duration, silences, chunk=CHUNK_SECONDS, search=BOUNDARY_SEARCH):
    """Split [0, duration] into ~chunk-long pieces, cutting inside silences."""
    if duration <= chunk * 1.25:
        return [(0.0, float(duration))]
    cuts = []
    start = 0.0
    silences = sorted(silences)
    while duration - start > chunk * 1.25:
        target = start + chunk
        near = [s for s in silences if abs(s - target) <= search and s > start + chunk / 2]
        cut = min(near, key=lambda s: abs(s - target)) if near else target
        cuts.append(cut)
        start = cut
    edges = [0.0, *cuts, float(duration)]
    return [(round(a, 3), round(b, 3)) for a, b in zip(edges, edges[1:]) if b - a > 0.05]


def load_chunk(path, start, end, clean=False):
    """Decode exactly [start, end] of the first audio track to 16 kHz mono float32."""
    import numpy as np
    ffmpeg = _ffmpeg()
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'error',
           '-ss', f'{start:.3f}', '-t', f'{end - start:.3f}', '-i', str(path),
           '-vn', '-sn', '-dn', '-map', '0:a:0', '-ac', '1', '-ar', str(SAMPLE_RATE),
           *(['-af', CLEAN_FILTER] if clean else []),
           '-f', 'f32le', '-acodec', 'pcm_f32le', '-']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_hidden_startupinfo())
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode('utf-8', 'replace')[-800:] or 'FFmpeg decode failed')
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


# --------------------------------------------------------------------------
# Output formats
# --------------------------------------------------------------------------

def _stamp(seconds, sep=','):
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}'


def _short_stamp(seconds):
    s = int(seconds)
    return f'{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}'


def to_srt(segments):
    rows = []
    for i, seg in enumerate(segments, 1):
        rows.append(f"{i}\n{_stamp(seg['start'])} --> {_stamp(seg['end'])}\n{seg['text']}\n")
    return '\n'.join(rows)


def to_vtt(segments):
    rows = ['WEBVTT\n']
    for seg in segments:
        rows.append(f"{_stamp(seg['start'], '.')} --> {_stamp(seg['end'], '.')}\n{seg['text']}\n")
    return '\n'.join(rows)


def to_txt(segments, timestamps=False, paragraph_gap=2.0):
    """Readable text: sentences joined into paragraphs at pauses."""
    if timestamps:
        return '\n'.join(f"[{_short_stamp(s['start'])}] {s['text']}" for s in segments) + '\n'
    paragraphs, current, last_end = [], [], None
    for seg in segments:
        if current and last_end is not None and (seg['start'] - last_end >= paragraph_gap or len(current) >= 8):
            paragraphs.append(' '.join(current))
            current = []
        current.append(seg['text'])
        last_end = seg['end']
    if current:
        paragraphs.append(' '.join(current))
    return '\n\n'.join(paragraphs) + '\n'


def write_outputs(segments, out_dir, stem, formats, *, unique=True):
    from core_ops import unique_path
    writers = {
        'txt': ('_transcript.txt', lambda s: to_txt(s), 'utf-8-sig'),
        'txt_ts': ('_transcript_timestamps.txt', lambda s: to_txt(s, timestamps=True), 'utf-8-sig'),
        'srt': ('_transcript.srt', to_srt, 'utf-8'),
        'vtt': ('_transcript.vtt', to_vtt, 'utf-8'),
    }
    outputs = []
    for fmt in formats:
        suffix, render, encoding = writers[fmt]
        dest = unique_path(out_dir, stem + suffix) if unique else Path(out_dir) / (stem + suffix)
        dest.write_text(render(segments), encoding=encoding)
        outputs.append(dest)
    return outputs


# --------------------------------------------------------------------------
# Checkpoints (resume after cancel / crash / sleep)
# --------------------------------------------------------------------------

def _fingerprint(path, quality, language):
    st = Path(path).stat()
    key = f'{Path(path).resolve()}|{st.st_size}|{int(st.st_mtime)}|{quality}|{language}|{CHECKPOINT_VERSION}'
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:24]


def checkpoint_path(out_dir, source):
    return Path(out_dir) / f'.{Path(source).stem}.morphix-transcript.json'


def _load_checkpoint(cp: Path, fingerprint):
    try:
        data = json.loads(cp.read_text(encoding='utf-8'))
        if data.get('fingerprint') == fingerprint and isinstance(data.get('done'), dict):
            return data
    except (OSError, ValueError):
        pass
    return None


def _save_checkpoint(cp: Path, data):
    tmp = cp.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, cp)


# --------------------------------------------------------------------------
# Keep the computer awake during multi-hour jobs
# --------------------------------------------------------------------------

class KeepAwake:
    def __enter__(self):
        self._proc = None
        try:
            if sys.platform == 'darwin':
                self._proc = subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        try:
            if self._proc is not None:
                self._proc.terminate()
            elif os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass
        return False


# --------------------------------------------------------------------------
# Model wrapper
# --------------------------------------------------------------------------

class WhisperBackend:
    """Thin wrapper; tests swap it for a fake so CI never needs model weights."""

    def __init__(self, quality):
        if not engine_available():
            raise RuntimeError(_t('The speech engine is not installed. Run Launch_Morphix_Mac.command once while connected to the internet.'))
        folder = model_dir(quality)
        if folder is None:
            raise RuntimeError(_t('The speech model “{model}” is not downloaded yet.\nOpen Morphix Studio → '
                                  'Speech models → Download (one time, needs internet). After that, '
                                  'transcription works fully offline.', model=_t(MODELS[quality][2])))
        from faster_whisper import WhisperModel
        threads = max(1, (os.cpu_count() or 4) - 1)
        compute, self.beam, self.patience = DECODING.get(quality, DECODING['best'])
        self.model = WhisperModel(str(folder), device='cpu', compute_type=compute,
                                  cpu_threads=threads, local_files_only=True)

    def detect(self, audio):
        """Return 'ar' or 'en' — whichever the model finds more likely."""
        try:
            # Skip leading music/silence (VAD) and vote over several windows.
            _lang, _p, probs = self.model.detect_language(
                audio, vad_filter=True, language_detection_segments=4)
            scores = dict(probs)
        except Exception:
            _segs, info = self.model.transcribe(audio[:SAMPLE_RATE * 30], beam_size=1)
            scores = dict(info.all_language_probs or [])
        return 'ar' if scores.get('ar', 0) >= scores.get('en', 0) else 'en'

    def transcribe(self, audio, language, prompt=None):
        segments, _info = self.model.transcribe(
            audio, language=language, task='transcribe',
            beam_size=self.beam, best_of=5, patience=self.patience,
            initial_prompt=prompt or STYLE_PROMPTS.get(language),
            # Context inside a ~10 min part improves spelling of names/terms;
            # temperature fallback + compression check stop repetition loops.
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters={'threshold': 0.35, 'min_silence_duration_ms': 700,
                            'speech_pad_ms': 500},
            no_speech_threshold=0.6, compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            word_timestamps=True, hallucination_silence_threshold=2.0,
            temperature=(0.0, 0.2, 0.4, 0.6, 0.8))
        for seg in segments:
            yield float(seg.start), float(seg.end), seg.text.strip()


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------

def transcribe_media(paths, out_dir, progress=None, *, language='auto', quality=DEFAULT_QUALITY,
                     formats=('txt', 'srt'), status=None, backend_factory=None,
                     chunk_seconds=CHUNK_SECONDS, ui_lang='en', clean_audio=True):
    """Transcribe each audio/video file; returns the created output files."""
    global _LANG
    _LANG = ui_lang
    if language not in LANGUAGES:
        raise ValueError('Language must be auto, ar or en')
    formats = [f for f in formats if f in ('txt', 'txt_ts', 'srt', 'vtt')] or ['txt']
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    say = status or (lambda _msg: None)
    emit = progress or (lambda _v: None)
    say(_t('Loading the speech model (offline)…'))
    backend = (backend_factory or WhisperBackend)(quality)   # fail fast if missing
    outputs = []
    with KeepAwake():
        for file_index, source in enumerate(paths):
            source = Path(source)
            base = file_index / len(paths) * 100
            span = 100 / len(paths)
            prefix = f'[{file_index + 1}/{len(paths)}] ' if len(paths) > 1 else ''
            say(prefix + _t('Analyzing the audio of {name}…', name=source.name))
            duration, silences = analyze_audio(
                source, lambda v: emit(int(base + span * 0.04 * v / 100)))
            chunks = plan_chunks(duration, silences, chunk_seconds)

            cp = checkpoint_path(out_dir, source)
            fingerprint = _fingerprint(source, quality, language)
            state = _load_checkpoint(cp, fingerprint)
            if state is None or state.get('chunks') != [list(c) for c in chunks]:
                state = {'fingerprint': fingerprint, 'source': str(source), 'quality': quality,
                         'language': language, 'detected': None,
                         'chunks': [list(c) for c in chunks], 'done': {}}
            elif state['done']:
                say(prefix + _t('Continuing {name} — {done} of {total} parts already done', name=source.name, done=len(state['done']), total=len(chunks)))

            partial = out_dir / f'{source.stem}_transcript.partial.txt'
            started = time.monotonic()
            processed_audio = 0.0
            for ci, (c_start, c_end) in enumerate(chunks):
                if str(ci) in state['done']:
                    continue
                audio = load_chunk(source, c_start, c_end, clean=clean_audio)
                if audio.size < SAMPLE_RATE // 4:
                    state['done'][str(ci)] = []
                    continue
                lang = language
                if lang == 'auto':
                    if not state.get('detected'):
                        state['detected'] = backend.detect(audio)
                    lang = state['detected']
                chunk_segments = []
                # Carry the end of the previous part as context, so sentences
                # and names continue correctly across part boundaries.
                previous = [seg['text'] for k in range(ci - 1, -1, -1)
                            for seg in reversed(state['done'].get(str(k), []))][:6]
                context = ' '.join(reversed(previous))[-220:]
                prompt = (STYLE_PROMPTS.get(lang, '') + ' ' + context).strip()
                for s, e, text in backend.transcribe(audio, lang, prompt=prompt):
                    if not text:
                        continue
                    chunk_segments.append({'start': round(c_start + s, 3),
                                           'end': round(c_start + min(e, c_end - c_start), 3),
                                           'text': text})
                    done_secs = sum(b - a for k, (a, b) in enumerate(chunks) if str(k) in state['done'])
                    frac = min(1.0, (done_secs + e) / duration)
                    emit(int(base + span * (0.04 + 0.95 * frac)))
                state['done'][str(ci)] = chunk_segments
                _save_checkpoint(cp, state)
                # Human-readable progress file the user can open at any time.
                ordered = [seg for k in range(len(chunks)) for seg in state['done'].get(str(k), [])]
                partial.write_text(to_txt(ordered, timestamps=True), encoding='utf-8-sig')

                processed_audio += c_end - c_start
                remaining = sum(b - a for k, (a, b) in enumerate(chunks) if str(k) not in state['done'])
                elapsed = time.monotonic() - started
                eta = elapsed / processed_audio * remaining if processed_audio else 0
                say(prefix + _t('{name}: part {done} of {total} · {pos} of {length} · about {mins} min left',
                                name=source.name, done=len(state['done']), total=len(chunks),
                                pos=_short_stamp(min(duration, c_end)), length=_short_stamp(duration),
                                mins=max(1, round(eta / 60))) if remaining else
                    prefix + _t('{name}: finishing…', name=source.name))
                emit(int(base + span * (0.04 + 0.95 * min(1.0, sum(
                    b - a for k, (a, b) in enumerate(chunks) if str(k) in state['done']) / duration))))

            segments = [seg for k in range(len(chunks)) for seg in state['done'].get(str(k), [])]
            if not segments:
                cp.unlink(missing_ok=True)
                partial.unlink(missing_ok=True)
                raise ValueError(_t('No speech was recognized in {name}.', name=source.name))
            outputs += write_outputs(segments, out_dir, source.stem, formats)
            cp.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
            emit(int(base + span))
    say(_t('Done.'))
    return outputs
