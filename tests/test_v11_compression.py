"""v1.1 compression tests (engine only; GUI still needs a macOS test)."""
import io
import sys
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compression_engine import image_quality, pdf_rewrite_params, flatten_for_jpeg, save_image_compressed, save_pdf_compressed


def test_strength_increases_jpeg_compression():
    assert image_quality(10) > image_quality(50) > image_quality(90)
    assert image_quality(-100) <= 95
    assert image_quality(999) >= 20


def test_transparent_png_becomes_white_not_black():
    src = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
    flat = flatten_for_jpeg(src)
    assert flat.getpixel((10, 10)) == (255, 255, 255)


def test_image_quality_controls_size(tmp_path):
    from PIL import ImageDraw
    image = Image.new('RGB', (800, 600), '#46779A')
    draw = ImageDraw.Draw(image)
    for n in range(700):
        draw.line((n, 0, 800-n, 600), fill=(n%255,(n*4)%255,(n*8)%255), width=2)
    high = tmp_path / 'light.jpg'
    low = tmp_path / 'strong.jpg'
    save_image_compressed(image, high, quality=image_quality(15))
    save_image_compressed(image, low, quality=image_quality(95))
    assert low.stat().st_size < high.stat().st_size
    with Image.open(low) as result:
        assert result.size == image.size


def test_resize_only_when_requested(tmp_path):
    im=Image.new('RGB', (1800, 1200), '#3581BC')
    full=tmp_path/'full.jpg'; reduced=tmp_path/'small.jpg'
    save_image_compressed(im, full, quality=50)
    save_image_compressed(im, reduced, quality=50, resize_max=1000)
    with Image.open(full) as src, Image.open(reduced) as dst:
        assert src.size == (1800,1200)
        assert max(dst.size) <= 1000


def test_pdf_compression_preserves_text_and_original(tmp_path):
    source=tmp_path/'original.pdf'; dest=tmp_path/'compressed.pdf'
    with fitz.open() as pdf:
        page=pdf.new_page()
        page.insert_text((70, 70), 'Morphix keeps selectable text')
        # Repeated large photo creates image content for compression.
        image=Image.new('RGB',(1200,1000),'#9FD0F0')
        import random
        rnd=random.Random(123)
        for x in range(0, 1200, 4):
            for y in range(0, 1000, 4):
                image.putpixel((x,y),(rnd.randrange(256),rnd.randrange(256),rnd.randrange(256)))
        stream=io.BytesIO(); image.save(stream,format='PNG')
        page.insert_image(fitz.Rect(40,100,550,600), stream=stream.getvalue())
        pdf.save(source)
    original_bytes=source.read_bytes()
    with fitz.open(source) as pdf:
        save_pdf_compressed(pdf,dest,strength=90)
    assert source.read_bytes() == original_bytes
    with fitz.open(dest) as result:
        assert 'Morphix keeps selectable text' in result[0].get_text()
    assert dest.stat().st_size <= source.stat().st_size


def test_pdf_params_stronger_downsample():
    assert pdf_rewrite_params(15) is None
    assert pdf_rewrite_params(85)['dpi_target'] < pdf_rewrite_params(50)['dpi_target']
