"""Formula image → LaTeX (offline, ONNX Runtime).

A compact re-implementation of RapidLaTeXOCR (Apache-2.0, RapidAI), which is
an ONNX port of pix2tex / LaTeX-OCR (MIT, Lukas Blecher). Greedy decoding,
no PyTorch needed. Works best on an image that contains one formula.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image

MAX_DIMS = (672, 192)
MIN_DIMS = (32, 32)
MEAN, STD = 0.7931, 0.1738
BOS, EOS, MAX_LEN = 1, 2, 512
FILES = ('image_resizer.onnx', 'encoder.onnx', 'decoder.onnx', 'tokenizer.json')


def _session(path):
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.enable_cpu_mem_arena = False
    opts.log_severity_level = 3
    return ort.InferenceSession(str(path), sess_options=opts, providers=['CPUExecutionProvider'])


def _pad(img: Image.Image, divable=32) -> Image.Image:
    """Crop to the ink, make it dark-on-white, pad to a multiple of 32."""
    data = np.array(img.convert('LA'))
    if data[..., -1].var() == 0:
        data = data[..., 0].astype(np.float32)
    else:
        data = (255 - data[..., -1]).astype(np.float32)
    span = data.max() - data.min()
    data = (data - data.min()) / (span if span else 1) * 255
    if data.mean() > 128:
        ink = data < 128
    else:
        ink = data > 128
        data = 255 - data
    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        raise ValueError('No formula found in the image.')
    a, b, w, h = xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    im = Image.fromarray(data[b:b + h, a:a + w].astype(np.uint8)).convert('L')
    dims = [divable * (x // divable + (1 if x % divable else 0)) for x in (w, h)]
    padded = Image.new('L', tuple(dims), 255)
    padded.paste(im, (0, 0, im.size[0], im.size[1]))
    return padded


def _minmax(img: Image.Image) -> Image.Image:
    ratios = [a / b for a, b in zip(img.size, MAX_DIMS)]
    if any(r > 1 for r in ratios):
        size = np.maximum(np.array(img.size) // max(ratios), 1).astype(int)
        img = img.resize(tuple(size), Image.BILINEAR)
    padded = tuple(max(d, m) for d, m in zip(img.size, MIN_DIMS))
    if padded != img.size:
        canvas = Image.new('L', padded, 255)
        canvas.paste(img, img.getbbox())
        img = canvas
    return img


def _tensor(img: Image.Image) -> np.ndarray:
    gray = np.array(img.convert('L'), dtype=np.float32)
    gray = (gray - MEAN * 255) / (STD * 255)
    return gray[None, None, ...].astype(np.float32)


def _clean(s: str) -> str:
    text_reg = r'(\\(operatorname|mathrm|text|mathbf)\s?\*? {.*?})'
    letter, noletter = '[a-zA-Z]', r'[\W_^\d]'
    names = [x[0].replace(' ', '') for x in re.findall(text_reg, s)]
    s = re.sub(text_reg, lambda m: str(names.pop(0)), s)
    news = s
    while True:
        s = news
        news = re.sub(r'(?!\\ )(%s)\s+?(%s)' % (noletter, noletter), r'\1\2', s)
        news = re.sub(r'(?!\\ )(%s)\s+?(%s)' % (noletter, letter), r'\1\2', news)
        news = re.sub(r'(%s)\s+?(%s)' % (letter, noletter), r'\1\2', news)
        if news == s:
            break
    return s


class LatexOCR:
    def __init__(self, folder):
        folder = Path(folder)
        missing = [f for f in FILES if not (folder / f).is_file()]
        if missing:
            raise FileNotFoundError('Formula model files missing: ' + ', '.join(missing))
        from tokenizers import Tokenizer
        self.resizer = _session(folder / 'image_resizer.onnx')
        self.encoder = _session(folder / 'encoder.onnx')
        self.decoder = _session(folder / 'decoder.onnx')
        self.tokenizer = Tokenizer.from_file(str(folder / 'tokenizer.json'))

    def _resize_loop(self, img: Image.Image) -> np.ndarray:
        base = _minmax(_pad(img)).convert('RGB')
        r, w, h = 1.0, base.size[0], base.size[1]
        final = None
        for _ in range(10):
            h = max(1, int(h * r))
            resized = base.resize((max(1, int(w)), h), Image.BILINEAR if r > 1 else Image.LANCZOS)
            padded = _pad(_minmax(resized))
            final = _tensor(padded)
            out = self.resizer.run(None, {self.resizer.get_inputs()[0].name: final})[0]
            w = (int(np.argmax(out, axis=-1).reshape(-1)[0]) + 1) * 32
            if w == padded.size[0]:
                break
            r = w / padded.size[0]
        return final

    def __call__(self, image) -> str:
        img = image if isinstance(image, Image.Image) else Image.open(image)
        x = self._resize_loop(img)
        context = self.encoder.run(None, {self.encoder.get_inputs()[0].name: x})[0]
        names = [i.name for i in self.decoder.get_inputs()]
        out = np.array([[BOS]], dtype=np.int64)
        for _ in range(MAX_LEN):
            mask = np.ones_like(out, dtype=bool)
            logits = self.decoder.run(None, dict(zip(names, [out, mask, context])))[0][:, -1, :]
            token = int(np.argmax(logits, axis=-1)[0])
            out = np.concatenate([out, [[token]]], axis=-1)
            if token == EOS:
                break
        tokens = out[0, 1:].tolist()
        text = self.tokenizer.decode(tokens)
        text = ''.join(text.split(' ')).replace('Ġ', ' ')
        for t in ('[EOS]', '[BOS]', '[PAD]'):
            text = text.replace(t, '')
        return _clean(text.strip())
