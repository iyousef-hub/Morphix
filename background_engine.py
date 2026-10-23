"""Offline background removal that keeps the original image quality.

The model only predicts a transparency mask (at 1024×1024). The mask is then
scaled up to the photo's real size and applied as an alpha channel, so every
original pixel is kept exactly as it was — same resolution, no re-compression
(the result is saved as a lossless PNG).

Models (downloaded once, then fully offline):
  best → BiRefNet-general (MIT licence, ~0.97 GB): excellent hair and fine edges
  fast → ISNet general-use (Apache-2.0, ~0.18 GB): quicker, good for simple shapes
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

MODELS = {
    # Default: excellent for people, products, animals and objects; ~1 GB RAM.
    'standard': ('isnet-general-use.onnx', '≈ 180 MB', 'Standard (ISNet) — recommended',
                 (0.485, 0.456, 0.406), (1.0, 1.0, 1.0), 'minmax'),
    # Finest hair/fur edges; needs a Mac with 16 GB of memory or more.
    'best': ('BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx', '≈ 220 MB', 'Finest edges (BiRefNet) — 16 GB RAM',
             (0.485, 0.456, 0.406), (0.229, 0.224, 0.225), 'sigmoid'),
}
MIN_RAM_GB = {'standard': 4, 'best': 15}


def total_ram_gb():
    try:
        if sys.platform == 'darwin':
            import subprocess
            return int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout) / 2**30
        if os.name == 'nt':
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 2**30
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30
    except Exception:
        return 0.0


def quality_allowed(quality):
    ram = total_ram_gb()
    return ram == 0.0 or ram >= MIN_RAM_GB.get(quality, 0)
BASE_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/'
SIZE = 1024
_LANG = 'en'


def _t(text, **fmt):
    try:
        from i18n import trl
        return trl(_LANG, text, **fmt)
    except Exception:
        return text.format(**fmt) if fmt else text


def models_root() -> Path:
    from transcription_engine import models_root as root
    return root() / 'background'


def model_path(quality):
    name = MODELS[quality][0]
    for folder in (Path(__file__).resolve().parent / 'assets' / 'background_models',
                   Path(getattr(sys, '_MEIPASS', '/nonexistent')) / 'assets' / 'background_models',
                   models_root()):
        if (folder / name).is_file() and (folder / name).stat().st_size > 10_000_000:
            return folder / name
    return None


def download_model(quality, progress=None, status_cb=None, ui_lang='en'):
    global _LANG
    _LANG = ui_lang
    name, size = MODELS[quality][0], MODELS[quality][1]
    dest = models_root() / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if status_cb:
        status_cb(_t('Downloading the background model ({size}) — one time only…', size=size))
    tmp = dest.with_suffix('.part')
    try:
        with urllib.request.urlopen(BASE_URL + name, timeout=60) as resp, open(tmp, 'wb') as out:
            total = int(resp.headers.get('Content-Length') or 0)
            done = 0
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if progress and total:
                    progress(min(99, done * 100 // total))
        os.replace(tmp, dest)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(_t('The model could not be downloaded. Please check your internet connection '
                              'and try again.') + f'\n{exc}') from exc
    if progress:
        progress(100)
    return dest


class _Session:
    _cache = {}

    def __init__(self, quality):
        path = model_path(quality)
        if path is None:
            raise RuntimeError(_t('The background-removal model is not downloaded yet. It downloads '
                                  'automatically the first time (internet needed once).'))
        import onnxruntime as ort
        key = str(path)
        if key not in self._cache:
            try:
                ort.disable_telemetry_events()
            except Exception:
                pass
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = max(1, (os.cpu_count() or 4) - 1)
            # Lower peak memory (the large model otherwise needs a lot of RAM).
            opts.enable_cpu_mem_arena = False
            opts.enable_mem_pattern = False
            # BiRefNet's graph balloons in memory when ORT pre-optimises it.
            opts.graph_optimization_level = (ort.GraphOptimizationLevel.ORT_DISABLE_ALL
                                             if 'BiRefNet' in key else ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
            self._cache[key] = ort.InferenceSession(str(path), opts, providers=['CPUExecutionProvider'])
        self.session = self._cache[key]
        _, _, _, self.mean, self.std, self.post = MODELS[quality]

    def mask(self, rgb):
        """Return an 'L' mask the size of `rgb` (PIL image, RGB)."""
        import numpy as np
        from PIL import Image
        small = rgb.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        arr = np.asarray(small, dtype=np.float32)
        arr = arr / max(float(arr.max()), 1e-6)
        arr = (arr - np.array(self.mean, np.float32)) / np.array(self.std, np.float32)
        tensor = arr.transpose(2, 0, 1)[None].astype(np.float32)
        out = self.session.run(None, {self.session.get_inputs()[0].name: tensor})[0][0, 0]
        if self.post == 'sigmoid':
            out = 1.0 / (1.0 + np.exp(-out))
        lo, hi = float(out.min()), float(out.max())
        out = (out - lo) / max(hi - lo, 1e-6)
        m = Image.fromarray((out * 255).clip(0, 255).astype('uint8'), 'L')
        # Smooth, high-quality upscale of the mask to the photo's real size.
        return m.resize(rgb.size, Image.Resampling.LANCZOS)


def remove_background(paths, out_dir, progress=None, *, quality='standard', background='transparent',
                      status=None, ui_lang='en'):
    """Create '<name>_no_bg.png' (or .jpg on a solid colour) for each image."""
    global _LANG
    _LANG = ui_lang
    from PIL import Image, ImageOps
    from core_ops import unique_path
    say = status or (lambda _m: None)
    if quality not in MODELS:
        quality = 'standard'
    if not quality_allowed(quality):
        say(_t('This Mac has too little memory for “Finest edges”; using Standard instead.'))
        quality = 'standard'
    if model_path(quality) is None:
        say(_t('Downloading the background model ({size}) — one time only…', size=MODELS[quality][1]))
        download_model(quality, None, None, ui_lang)
    session = _Session(quality)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for i, src in enumerate(paths, 1):
        src = Path(src)
        say(_t('Removing the background: {name} ({i} of {n})…', name=src.name, i=i, n=len(paths)))
        with Image.open(src) as original:
            img = ImageOps.exif_transpose(original)
            icc = original.info.get('icc_profile')
            rgb = img.convert('RGB')
            alpha = session.mask(rgb)
            if img.mode == 'RGBA':           # keep any transparency the photo already had
                from PIL import ImageChops
                alpha = ImageChops.multiply(alpha, img.getchannel('A'))
            if background == 'transparent':
                result = rgb.copy()
                result.putalpha(alpha)
                dest = unique_path(out_dir, src.stem + '_no_bg.png')
                result.save(dest, format='PNG', optimize=False, icc_profile=icc)
            else:
                colour = {'white': (255, 255, 255), 'black': (0, 0, 0)}.get(background, (255, 255, 255))
                canvas = Image.new('RGB', rgb.size, colour)
                canvas.paste(rgb, mask=alpha)
                dest = unique_path(out_dir, src.stem + f'_{background}_bg.png')
                canvas.save(dest, format='PNG', icc_profile=icc)
        outputs.append(dest)
        if progress:
            progress(round(i * 100 / len(paths)))
    return outputs
