"""Pure-Pillow crop/rotation engine shared by the quick editor and tests.

No Qt import; original files are never overwritten.
"""
from pathlib import Path
from PIL import Image


def rotate_image(image: Image.Image, angle: float) -> Image.Image:
    """Rotate counter-clockwise by any number of degrees, expanding canvas."""
    mode = 'RGBA' if image.mode in ('RGBA', 'LA', 'P') else 'RGB'
    result = image.convert(mode)
    return result.rotate(float(angle), resample=Image.Resampling.BICUBIC,
                         expand=True,
                         fillcolor=(0, 0, 0, 0) if mode == 'RGBA' else (255, 255, 255))


def export_image_edit(image: Image.Image, output_path, *, angle=0, crop=None, original_path=None):
    """Save independent edited copy; crop=(x0,y0,x1,y1) normalized to rotated image."""
    dest = Path(output_path)
    if original_path is not None and dest.resolve() == Path(original_path).resolve():
        raise ValueError('The original image must not be overwritten.')
    result = rotate_image(image, angle)
    if crop is not None:
        x0, y0, x1, y1 = map(float, crop)
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError('Invalid crop rectangle (expected normalized coordinates).')
        bounds = (round(x0 * result.width), round(y0 * result.height),
                  round(x1 * result.width), round(y1 * result.height))
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            raise ValueError('Crop area is too small.')
        result = result.crop(bounds)
    if dest.suffix.lower() in ('.jpg', '.jpeg'):
        if result.mode == 'RGBA':
            background = Image.new('RGB', result.size, 'white')
            background.paste(result, mask=result.getchannel('A'))
            result = background
        else:
            result = result.convert('RGB')
    result.save(dest)
    return dest
