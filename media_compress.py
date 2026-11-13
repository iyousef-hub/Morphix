"""Compress video and audio (Morphix 1.11).

Three ways, for one file or many:
* recommended — the best balance of size and quality, no choices needed
* strength    — a 0–100 slider: lighter keeps more quality, stronger makes smaller files
* target      — every file ends up at or under a size (e.g. 25 MB), however big it was

plan() predicts the result for each file (resolution, bitrate, size and a quality
level with a plain-language message) so the window can warn before anything runs;
compress() then does the work with FFmpeg (H.264 + AAC in MP4, or AAC / MP3 audio).
Target sizes use two-pass encoding so files land just under the limit.
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from core_ops import unique_path

VIDEO_EXT = ('.mp4', '.mov', '.m4v', '.mkv', '.avi', '.webm', '.wmv', '.flv', '.3gp', '.mpg', '.mpeg', '.ts')
AUDIO_EXT = ('.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus', '.wma', '.aiff', '.aif', '.amr')

MB = 1024 * 1024
# Long-side sizes tried when a picture must get smaller to stay clear
LADDER = (3840, 2560, 1920, 1280, 960, 854, 640, 426)
QUALITY = ('very_poor', 'low', 'acceptable', 'good', 'excellent')
MESSAGES = {
    'excellent': 'Excellent — looks the same as the original.',
    'good': 'Good — hard to notice any difference.',
    'acceptable': 'Acceptable — slightly softer, fine for sharing and watching on a phone.',
    'low': 'Low — blurry in motion and fine details are lost. OK for a quick share only.',
    'very_poor': 'Very poor — heavy blocks and smearing. Choose a bigger size or lighter compression.',
}
AUDIO_MESSAGES = {
    'excellent': 'Excellent — sounds the same as the original.',
    'good': 'Good — clear music and voice.',
    'acceptable': 'Acceptable — clear voice; music loses some richness.',
    'low': 'Low — voice is understandable but sounds thin.',
    'very_poor': 'Very poor — muffled sound. Choose a bigger size or lighter compression.',
}


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------------ probe
_DUR = re.compile(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)')
_BITRATE = re.compile(r'bitrate: (\d+) kb/s')
_VIDEO = re.compile(r'Stream #\S+.*?Video: (\w+).*?, (\d{2,5})x(\d{2,5})')
_FPS = re.compile(r'(\d+(?:\.\d+)?) fps')
_ROTATE = re.compile(r'(?:rotate\s*:\s*|rotation of )(-?\d+(?:\.\d+)?)')


def probe(path):
    """Duration, size, streams, picture size and frame rate of a media file."""
    path = Path(path)
    err = subprocess.run([_ffmpeg(), '-hide_banner', '-i', str(path)], capture_output=True, text=True,
                         errors='replace').stderr
    m = _DUR.search(err)
    duration = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else 0.0
    info = {'path': str(path), 'name': path.name, 'size': path.stat().st_size, 'duration': duration,
            'video': False, 'audio': 'Audio:' in err, 'width': 0, 'height': 0, 'fps': 30.0,
            'bitrate': 0}
    b = _BITRATE.search(err)
    if b:
        info['bitrate'] = int(b.group(1))
    elif duration:
        info['bitrate'] = int(info['size'] * 8 / 1000 / duration)
    for line in err.splitlines():
        v = _VIDEO.search(line)
        if v and 'attached pic' not in line and v.group(1) not in ('mjpeg', 'png', 'bmp'):
            w, h = int(v.group(2)), int(v.group(3))
            f = _FPS.search(line)
            info.update(video=True, width=w, height=h, fps=float(f.group(1)) if f else 30.0)
            break
    rot = _ROTATE.search(err)
    if info['video'] and rot and abs(float(rot.group(1))) % 180 == 90:
        info['width'], info['height'] = info['height'], info['width']   # phone videos shot upright
    info['fps'] = max(1.0, min(info['fps'], 120.0))
    return info


# ------------------------------------------------------------------ planning
def _even(x):
    return max(2, int(round(x / 2.0)) * 2)


def _fit(w, h, long_side):
    """Picture size with its long side at most long_side (never upscaled)."""
    if max(w, h) <= long_side:
        return _even(w), _even(h)
    s = long_side / max(w, h)
    return _even(w * s), _even(h * s)


def _bpp(kbps, w, h, fps):
    return kbps * 1000 / max(1.0, w * h * fps)


def _video_level(bpp, short_side):
    level = 4 if bpp >= 0.10 else 3 if bpp >= 0.065 else 2 if bpp >= 0.04 else 1 if bpp >= 0.022 else 0
    if short_side <= 270:       # tiny picture: never better than "low"
        level = min(level, 1)
    elif short_side <= 360:
        level = min(level, 2)
    return level


def _audio_level(kbps):
    return 4 if kbps >= 160 else 3 if kbps >= 112 else 2 if kbps >= 80 else 1 if kbps >= 48 else 0


def _crf_bpp(crf):
    """Typical bits per pixel of H.264 'medium' at a CRF (halves every +6)."""
    return 0.11 * 2 ** ((23 - crf) / 6.0)


def _strength_settings(strength):
    s = max(0, min(100, int(strength)))
    crf = round(19 + s * 0.19)                       # 19 … 38
    long_side = 99999 if s < 45 else 1920 if s < 70 else 1280 if s < 85 else 854
    audio = 192 if s < 20 else 160 if s < 40 else 128 if s < 60 else 96 if s < 80 else 64
    return crf, long_side, audio


def plan(info, mode='recommended', strength=50, target_mb=25.0, keep_resolution=False):
    """What will happen to one file: settings, estimated size, quality level and message."""
    d = max(info['duration'], 0.1)
    p = {'name': info['name'], 'size': info['size'], 'video': info['video'], 'audio': info['audio'],
         'duration': info['duration'], 'mode': mode, 'note': ''}
    if not info['video'] and not info['audio']:
        p.update(ok=False, level=0, message='No video or audio found in this file.', est=info['size'])
        return p
    original_kbps = info['bitrate'] or info['size'] * 8 / 1000 / d

    if not info['video']:                                   # ---------------- audio only
        if mode == 'target':
            budget = target_mb * MB * 8 * 0.97 / 1000 / d
            kbps = int(max(16, min(256, budget)))
            if info['size'] <= target_mb * MB:
                kbps = int(min(kbps, max(32, original_kbps)))
        elif mode == 'strength':
            kbps = _strength_settings(strength)[2]
        else:
            kbps = 128
        kbps = int(min(kbps, max(32, original_kbps)))       # never more than the source has
        est = kbps * 1000 / 8 * d * 1.01
        level = _audio_level(kbps)
        p.update(ok=True, audio_kbps=kbps, est=est, level=level, message=AUDIO_MESSAGES[QUALITY[level]])
        if mode == 'target' and info['size'] <= target_mb * MB:
            p['note'] = 'already_small'
        if mode == 'target' and kbps <= 16 and budget < 16:
            p.update(ok=False, level=0, message='This recording is too long to fit in that size. Choose a bigger size.')
        return p

    w0, h0, fps = info['width'], info['height'], info['fps']   # ---------------- video
    has_audio = info['audio']
    if mode == 'target':
        budget = target_mb * MB * 8 * 0.965 / 1000 / d          # kbit/s for everything
        audio = 0
        if has_audio:
            audio = next((a for a in (128, 96, 64, 48, 32) if a <= budget * 0.18), 32)
        if has_audio and budget < 70:
            audio = 24 if budget >= 40 else 16                  # squeeze the sound too
        video = budget - audio - 2
        out_fps = fps
        if video < 40:
            out_fps = min(fps, 15.0)                            # tiny budget: fewer frames, still watchable
        if video < 10:
            p.update(ok=False, level=0, est=target_mb * MB,
                     message='This video is too long to fit in that size. Choose a bigger size.')
            return p
        if keep_resolution:
            w, h = _even(w0), _even(h0)
        else:
            w, h = _fit(w0, h0, LADDER[-1])
            for side in LADDER:
                cw, ch = _fit(w0, h0, side)
                if _bpp(video, cw, ch, out_fps) >= 0.06:
                    w, h = cw, ch
                    break
            if _bpp(video, w, h, out_fps) < 0.035 and out_fps > 24:
                out_fps = 24.0
            if _bpp(video, w, h, out_fps) < 0.02 and out_fps > 15:
                out_fps = 15.0
        level = _video_level(_bpp(video, w, h, out_fps), min(w, h))
        est = (video + audio) * 1000 / 8 * d
        if info['size'] <= target_mb * MB and mode == 'target':
            p['note'] = 'already_small'
        p.update(ok=True, width=w, height=h, fps=out_fps, video_kbps=int(video), audio_kbps=audio,
                 crf=None, est=min(est, target_mb * MB), level=level)
    else:
        if mode == 'strength':
            crf, long_side, audio = _strength_settings(strength)
        else:
            crf, long_side, audio = 24, 1920, 128
        w, h = (_even(w0), _even(h0)) if keep_resolution else _fit(w0, h0, long_side)
        est_kbps = _crf_bpp(crf) * w * h * min(fps, 60) / 1000
        est_kbps = min(est_kbps, original_kbps * 0.95)          # re-encoding rarely grows a file
        audio = audio if has_audio else 0
        level = _video_level(_bpp(est_kbps, w, h, min(fps, 60)), min(w, h))
        if crf <= 23:
            level = max(level, 3)
        p.update(ok=True, width=w, height=h, fps=fps, crf=crf, video_kbps=None, audio_kbps=audio,
                 est=(est_kbps + audio) * 1000 / 8 * d, level=level)
        if p['est'] >= info['size'] * 0.9:
            p['note'] = 'little_gain'
    p['message'] = MESSAGES[QUALITY[p['level']]]
    if (w, h) != (_even(w0), _even(h0)):
        p['resized'] = f'{max(w, h)}×{min(w, h)}' if w >= h else f'{w}×{h}'
    return p


def summary(plans):
    """The weakest quality across files decides the warning shown."""
    ok = [p for p in plans if p.get('ok')]
    if not ok:
        return 0, plans[0]['message'] if plans else ''
    worst = min(ok, key=lambda p: p['level'])
    return worst['level'], worst['message']


# ------------------------------------------------------------------ encoding
def _run(args, duration, progress, base, span):
    from tools_engine import run_ffmpeg
    run_ffmpeg(args, duration, progress, base, span)


def _video_filters(p, info):
    vf = []
    if (p['width'], p['height']) != (_even(info['width']), _even(info['height'])):
        vf.append(f"scale={p['width']}:{p['height']}:flags=lanczos")
    else:
        vf.append("scale='trunc(iw/2)*2':'trunc(ih/2)*2'")
    if p.get('fps') and p['fps'] < info['fps'] - 0.5:
        vf.append(f"fps={p['fps']:g}")
    return ','.join(vf)


def compress_one(src, out_dir, p, info, progress=None, base=0, span=100):
    src = Path(src)
    if not p.get('ok'):
        raise ValueError(f"{src.name}: {p['message']}")
    d = info['duration']
    if not info['video']:
        mp3 = src.suffix.lower() == '.mp3'
        out = unique_path(out_dir, f'{src.stem}_compressed.{"mp3" if mp3 else "m4a"}')
        codec = (['-c:a', 'libmp3lame'] if mp3 else ['-c:a', 'aac', '-movflags', '+faststart'])
        channels = ['-ac', '1'] if p['audio_kbps'] <= 48 else []
        _run(['-i', str(src), '-vn', '-map_metadata', '0', *codec, '-b:a', f"{p['audio_kbps']}k", *channels,
              str(out)], d, progress, base, span)
        return out
    out = unique_path(out_dir, f'{src.stem}_compressed.mp4')
    vf = _video_filters(p, info)
    common = ['-map', '0:v:0', '-vf', vf, '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p',
              '-profile:v', 'high', '-map_metadata', '0']
    audio = (['-map', '0:a:0?', '-c:a', 'aac', '-b:a', f"{p['audio_kbps']}k", '-ac', '2']
             if info['audio'] and p.get('audio_kbps') else ['-an'])
    if p.get('crf') is not None:
        _run(['-i', str(src), *common, '-crf', str(p['crf']), *audio, '-movflags', '+faststart', str(out)],
             d, progress, base, span)
        return out
    kbps = p['video_kbps']
    rate = ['-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.45)}k', '-bufsize', f'{int(kbps * 2)}k']
    tmp = Path(tempfile.mkdtemp(prefix='morphix_2pass_'))
    try:
        log = str(tmp / 'pass')
        null = 'NUL' if __import__('os').name == 'nt' else '/dev/null'
        _run(['-i', str(src), *common, *rate, '-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', null],
             d, progress, base, span // 2)
        _run(['-i', str(src), *common, *rate, '-pass', '2', '-passlogfile', log, *audio,
              '-movflags', '+faststart', str(out)], d, progress, base + span // 2, span - span // 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def compress(paths, out_dir, progress=None, *, mode='recommended', strength=50, target_mb=25.0,
             keep_resolution=False, status=None):
    """Compress every file. Target mode re-tries once (a little smaller) if a file came out too big."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    n = len(paths)
    for i, src in enumerate(paths):
        info = probe(src)
        p = plan(info, mode, strength, target_mb, keep_resolution)
        base, span = i * 100 // n, 100 // n
        if status:
            status(f'{i + 1}/{n} · {info["name"]}')
        if mode == 'target' and p.get('note') == 'already_small':
            # Already under the limit: keep it exactly as it is (a copy, original quality).
            dest = unique_path(out_dir, f'{Path(src).stem}_compressed{Path(src).suffix}')
            shutil.copy2(src, dest)
            outputs.append(dest)
            continue
        out = compress_one(src, out_dir, p, info, progress, base, span)
        if mode == 'target' and out.stat().st_size > target_mb * MB:
            out.unlink()
            for key in ('video_kbps', 'audio_kbps'):
                if p.get(key):
                    p[key] = max(16, int(p[key] * 0.88))
            out = compress_one(src, out_dir, p, info, progress, base, span)
        outputs.append(out)
    if progress:
        progress(100)
    return outputs


def is_media(path):
    return str(path).lower().endswith(VIDEO_EXT + AUDIO_EXT)
