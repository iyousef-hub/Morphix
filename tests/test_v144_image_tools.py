"""Real file output tests for quick crop/rotate: preserve originals."""
from PIL import Image
import pytest
from image_tools import rotate_image, export_image_edit


def test_crop_to_center_quarter_and_preserve_original(tmp_path):
    source=tmp_path/'original.png'
    Image.new('RGB',(400,200),'blue').save(source)
    output=tmp_path/'original_edited.png'
    result=export_image_edit(Image.open(source), output, crop=(.25,.25,.75,.75),original_path=source)
    assert result==output
    with Image.open(output) as img: assert img.size==(200,100)
    with Image.open(source) as img: assert img.size==(400,200)


def test_rotation_free_and_right_angle(tmp_path):
    im=Image.new('RGB',(300,100),'red')
    assert rotate_image(im,90).size==(100,300)
    free=rotate_image(im,17)
    assert free.width>300 and free.height>100
    dest=tmp_path/'free.jpg'
    export_image_edit(im,dest,angle=17)
    with Image.open(dest) as output: assert output.size==free.size


def test_transparency_exports_to_jpeg_without_black_background(tmp_path):
    im=Image.new('RGBA',(50,50),(0,0,0,0))
    out=tmp_path/'transparent.jpg'
    export_image_edit(im,out)
    with Image.open(out) as img:
        assert img.mode=='RGB'
        assert min(img.getpixel((25,25)))>235


def test_invalid_crop_or_overwriting_original_rejected(tmp_path):
    source=tmp_path/'test.png'
    Image.new('RGB',(80,80),'white').save(source)
    with pytest.raises(ValueError, match='overwritten'):
        export_image_edit(Image.open(source),source,original_path=source)
    with pytest.raises(ValueError,match='Invalid crop'):
        export_image_edit(Image.open(source),tmp_path/'out.png',crop=(.9,0,.1,1))
