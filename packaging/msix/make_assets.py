"""Store/tile images for the MSIX, made from assets/morphix_logo.png."""
import sys
from pathlib import Path
from PIL import Image

src = Image.open(sys.argv[1]).convert('RGBA')
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)


def square(size, pad=0.0):
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    inner = max(1, round(size * (1 - 2 * pad)))
    logo = src.resize((inner, inner), Image.LANCZOS)
    canvas.paste(logo, ((size - inner) // 2, (size - inner) // 2), logo)
    return canvas


def wide(w, h):
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    inner = round(h * 0.8)
    logo = src.resize((inner, inner), Image.LANCZOS)
    canvas.paste(logo, ((w - inner) // 2, (h - inner) // 2), logo)
    return canvas


square(50).save(out / 'StoreLogo.png')
square(150, 0.12).save(out / 'Square150x150Logo.png')
square(71, 0.1).save(out / 'Square71x71Logo.png')
square(310, 0.12).save(out / 'Square310x310Logo.png')
square(44).save(out / 'Square44x44Logo.png')
wide(310, 150).save(out / 'Wide310x150Logo.png')
for t in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
    img = square(t)
    img.save(out / f'Square44x44Logo.targetsize-{t}.png')
    img.save(out / f'Square44x44Logo.targetsize-{t}_altform-unplated.png')
    img.save(out / f'Square44x44Logo.targetsize-{t}_altform-lightunplated.png')
print('assets in', out)
