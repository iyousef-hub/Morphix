"""Regression tests for v1.4 features; native UI tested separately on macOS."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf
import pytest
from PIL import Image, ImageDraw, ImageFont
from page_ranges import extract_ranges, validate_ranges
from file_intelligence import selection_profile, file_summary
from ocr_engine import extract_image_text


def make_pdf(path, count):
    with pymupdf.open() as d:
        for i in range(count):
            d.new_page().insert_text((42, 65), f'Page {i + 1} - Morphix')
        d.save(path)


def test_single_range(tmp_path):
    src=tmp_path/'100pages.pdf'
    make_pdf(src,100)
    out=extract_ranges(src,tmp_path,[(8,13)])
    assert len(out)==1
    with pymupdf.open(out[0]) as d:
        assert len(d)==6
        assert 'Page 8' in d[0].get_text()
        assert 'Page 13' in d[-1].get_text()


def test_multiple_parts(tmp_path):
    src=tmp_path/'100pages.pdf'
    make_pdf(src,100)
    out=extract_ranges(src,tmp_path,[(1,25),(26,50),(51,100)],separate=True)
    assert len(out)==3
    assert [len(pymupdf.open(x)) for x in out]==[25,25,50]
    assert [p.name for p in out] == sorted(p.name for p in out)


def test_validation_includes_bounds_and_overlap():
    assert validate_ranges([(1, 10),(11, 20)],20)==[(1,10),(11,20)]
    with pytest.raises(ValueError): validate_ranges([(1,21)],20)
    with pytest.raises(ValueError): validate_ranges([(15,10)],20)
    with pytest.raises(ValueError): validate_ranges([(1,10),(10,20)],20)
    with pytest.raises(ValueError): validate_ranges([],20)


def test_image_ocr_english(tmp_path):
    font_candidates=list(Path('/usr/share/fonts').rglob('DejaVuSans.ttf'))
    if not font_candidates: pytest.skip('No test font')
    im=Image.new('RGB',(950,240),'white')
    ImageDraw.Draw(im).text((50,65),'Morphix Image Text',fill='black',font=ImageFont.truetype(str(font_candidates[0]),60))
    source=tmp_path/'ocr_sample.png'
    im.save(source)
    out=extract_image_text([source],tmp_path)
    assert len(out)==1
    assert 'Morphix Image Text' in out[0].read_text(encoding='utf-8-sig')


def test_profile_reflects_only_selected_set(tmp_path):
    p=tmp_path/'a.pdf'; im=tmp_path/'b.png'; zipf=tmp_path/'c.zip'
    p.write_bytes(b'%PDF-1.4\n'); im.write_bytes(b'\x89PNG\r\n\x1a\n'); zipf.write_bytes(b'123')
    assert selection_profile([p])=='pdf_single'
    assert selection_profile([im])=='image_single'
    assert selection_profile([p,im,zipf])=='mixed'
    assert file_summary([p,im,zipf])==['1 PDF','1 PNG','1 ZIP']


def test_wheel_actions_are_unified_and_reactive():
    source=(Path(__file__).resolve().parents[1]/'quickwheel.py').read_text()
    assert "'wheel_v14/' + profile" in source
    assert 'paths + self.sticky_added' in source
    assert 'self.current_paths + paths + self.sticky_added' not in source
    assert "'ocr_image_text': ('Extract text','text')" in source
    assert "'separate_pdf': ('Separate PDF','split')" in source
    assert "'pdf_single': ('One PDF', ['ocr_searchable_pdf','organize_pdf','sign_pdf','optimize_pdf'" in source

class Progress:
    def emit(self, value):
        assert 0 <= value <= 100


def test_real_worker_single_and_multi_ranges(tmp_path):
    pytest.importorskip('PySide6', reason='GUI-dependent worker needs PySide6')
    from main import execute
    source=tmp_path/'lecture.pdf'
    make_pdf(source,20)
    one=execute('split_pdf',[str(source)],str(tmp_path),Progress(), {'page_ranges':[(3,8)]})
    assert len(one)==1
    with pymupdf.open(one[0]) as d:
        assert len(d)==6
    parts=execute('separate_pdf',[str(source)],str(tmp_path),Progress(),{'page_ranges':[(1,5),(6,20)]})
    assert len(parts)==2
    assert [len(pymupdf.open(x)) for x in parts] == [5,15]


def test_real_worker_image_extract_text(tmp_path):
    pytest.importorskip('PySide6', reason='GUI-dependent worker needs PySide6')
    from main import execute
    font_candidates=list(Path('/usr/share/fonts').rglob('DejaVuSans.ttf'))
    if not font_candidates: pytest.skip('No test font')
    img=Image.new('RGB',(1050,250),'white')
    ImageDraw.Draw(img).text((35,70),'Lecture Morphix',font=ImageFont.truetype(str(font_candidates[0]),68),fill='black')
    src=tmp_path/'lecture.png';img.save(src)
    out=execute('ocr_image_text',[str(src)],str(tmp_path),Progress())
    assert 'Lecture Morphix' in out[0].read_text(encoding='utf-8-sig')
