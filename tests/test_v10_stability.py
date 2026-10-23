"""Tests run on Linux without installing a Qt GUI."""
from pathlib import Path
import io
import tarfile
import sys
import zipfile
import fitz
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_intelligence import selection_profile, file_summary, category_for
from core_ops import archive_files, extract_pdf_text
from native_hotkeys import matches_event, parse_shortcut, PHYSICAL_KEYS


def test_mixed_selection_overrides_pdf_tools(tmp_path):
    files=[]
    for name in ['a.pdf','b.pdf','c.png']:
        path=tmp_path/name
        if path.suffix=='.pdf':
            with fitz.open() as doc:
                doc.new_page()
                doc.save(path)
        else:
            Image.new('RGB',(2,2)).save(path)
        files.append(str(path))
    assert selection_profile(files[:2])=='pdf_multi'
    assert selection_profile(files)=='pdf_image_mix'
    assert file_summary(files)==['2 PDF','1 PNG']


def test_tar_gz_is_real_and_separate_from_zip(tmp_path):
    a=tmp_path/'a.txt'; a.write_text('hi')
    dest=archive_files([a],tmp_path,'tar.gz')[0]
    assert tarfile.is_tarfile(dest)
    with tarfile.open(dest,'r:gz') as f:
        assert f.extractfile('a.txt').read()==b'hi'
    other=archive_files([a],tmp_path,'zip')[0]
    assert zipfile.is_zipfile(other)


def test_physical_m_key_ignores_language():
    flags,key=parse_shortcut('<cmd>+<shift>+m')
    class FakeEvent:
        def modifierFlags(self): return flags
        def keyCode(self): return PHYSICAL_KEYS['m']
        def charactersIgnoringModifiers(self): return 'م'
    assert matches_event(FakeEvent(),flags,key)


def test_real_pdf_to_utf8_text(tmp_path):
    source=tmp_path/'document.pdf'
    with fitz.open() as d:
        page=d.new_page();page.insert_text((50,60),'English test')
        d.save(source)
    out=extract_pdf_text([source],tmp_path)[0]
    assert 'English test' in out.read_text(encoding='utf-8-sig')


def test_realtime_wheel_uses_clickable_child_buttons():
    source=(Path(__file__).parents[1] / 'quickwheel.py').read_text()
    assert 'class WheelActionButton(QToolButton)' in source
    assert 'self.clicked.connect(' in source
    assert 'self.rebuild_buttons()' in source
    assert 'paths + self.sticky_added' in source  # live Finder selection replaces, explicit additions persist
    assert 'draw_controls=True' in source
