"""Morphix 1.4.5: mixed image/PDF merges and explicit file ordering."""
from pathlib import Path
import sys
import io

import pytest
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdf_merge import merge_documents
from engine_core import execute
from file_intelligence import selection_profile, preserve_selected_order


class Progress:
    def __init__(self):
        self.values = []
    def emit(self, value):
        self.values.append(value)


def sample_pdf(path, markers=('PDF page 1', 'PDF page 2', 'PDF page 3')):
    with pymupdf.open() as doc:
        for marker in markers:
            p = doc.new_page(width=350, height=250)
            p.insert_text((50, 90), marker, fontsize=15)
        doc.save(path)


def test_pdf_and_jpeg_images_keep_supplied_order_and_full_pdf_pages(tmp_path):
    files = []
    for i, ext, color in [(1, 'png', 'red'), (2, 'png', 'green'), (3, 'jpeg', 'blue')]:
        p = tmp_path/f'{i:02}.{ext}'
        Image.new('RGB', (170, 100), color).save(p)
        files.append(str(p))
    source = tmp_path/'lecture.pdf'
    sample_pdf(source)
    last = tmp_path/'last.png'
    Image.new('RGB',(190,80),'yellow').save(last)
    ordered = files + [str(source), str(last)]
    assert selection_profile(ordered) == 'pdf_image_mix'
    progress=Progress()
    result = execute('merge_pdf', ordered, str(tmp_path), progress)[0]
    assert progress.values[-1] == 100
    with pymupdf.open(result) as pdf:
        assert pdf.page_count == 7
        for idx in (0,1,2,6):
            assert pdf[idx].get_images(), f'Expected image page at position {idx+1}'
        assert ['PDF page 1', 'PDF page 2', 'PDF page 3'] == [
            pdf[i].get_text().strip() for i in (3,4,5)]


def test_pdf_first_and_optimized_merge(tmp_path):
    src = tmp_path/'document.pdf'
    sample_pdf(src,('First PDF page','Second PDF page'))
    png = tmp_path/'photo.png'
    Image.new('RGBA',(50,100),(12,90,220,120)).save(png)
    out=execute('merge_optimize',[str(src),str(png)],str(tmp_path),Progress(), {'compression_strength':40})[0]
    with pymupdf.open(out) as doc:
        assert doc.page_count==3
        assert 'First PDF page' in doc[0].get_text()
        assert doc[2].get_images()


def test_input_does_not_become_alphabetized(tmp_path):
    z = tmp_path/'z_last_name.jpg'
    a = tmp_path/'a_first_name.png'
    Image.new('RGB',(100,100),'purple').save(z)
    Image.new('RGB',(101,101),'orange').save(a)
    result = execute('merge_pdf',[str(z),str(a)],str(tmp_path),Progress())[0]
    with pymupdf.open(result) as doc:
        assert [doc[i].rect.width for i in range(2)]==[100,101]


def test_unsupported_selection_is_rejected(tmp_path):
    pdf=tmp_path/'source.pdf'
    sample_pdf(pdf)
    misc=tmp_path/'unsupported.mp4'
    misc.write_bytes(b'not a real video')
    with pytest.raises(ValueError,match='only PDF and images'):
        execute('merge_pdf',[str(pdf),str(misc)],str(tmp_path),Progress())
    assert selection_profile([pdf,misc])=='mixed'


def test_missing_or_protected_file(tmp_path):
    png=tmp_path/'photo.png'
    Image.new('RGB',(5,5),'red').save(png)
    with pytest.raises(FileNotFoundError):
        merge_documents([png,tmp_path/'missing.pdf'])
    protected=tmp_path/'protected.pdf'
    with pymupdf.open() as d:
        d.new_page().insert_text((50,50),'secret')
        d.save(protected, encryption=pymupdf.PDF_ENCRYPT_AES_256,
               owner_pw='admin', user_pw='reader', permissions=0)
    with pytest.raises(ValueError,match='password'):
        merge_documents([protected,png])


def test_selection_order_preserved_on_incremental_highlight():
    assert preserve_selected_order(['b.pdf','a.png'], ['a.png','b.pdf','c.jpg']) == ['b.pdf','a.png','c.jpg']
    assert preserve_selected_order(['b.pdf','a.png','c.jpg'], ['c.jpg','a.png']) == ['a.png','c.jpg']
    assert preserve_selected_order([], ['c.jpg','b.pdf'])==['c.jpg','b.pdf']


def test_wheel_and_studio_wire_merge_review():
    quickwheel=(Path(__file__).resolve().parents[1]/'quickwheel.py').read_text()
    main=(Path(__file__).resolve().parents[1]/'main.py').read_text()
    assert "'pdf_image_mix': ('PDF + Images'" in quickwheel
    assert "if profile == 'pdf_image_mix':" in main
    assert "from merge_order_dialog import ask_merge_order" in main
    assert "from merge_order_dialog import ask_merge_order" in quickwheel
    assert "paths = ordered" in quickwheel
    assert "paths = ask_merge_order(paths, parent=self)" in main


def test_worker_process_protocol_with_mixed_file_inputs(tmp_path):
    import subprocess, json
    p=tmp_path/'page.pdf';sample_pdf(p,('TEXT PAGE',))
    img=tmp_path/'photo.png';Image.new('RGB',(200,150),'red').save(img)
    req=tmp_path/'request.json'
    req.write_text(json.dumps({'action':'merge_pdf','paths':[str(img),str(p)],'out_dir':str(tmp_path),'options':{}}))
    proc=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'worker_process.py'),str(req)],
                       capture_output=True,text=True,timeout=20)
    assert proc.returncode==0, proc.stdout+proc.stderr
    assert '"type": "completed"' in proc.stdout
    merged=tmp_path/'merged.pdf'
    with pymupdf.open(merged) as d:
        assert d.page_count==2
        assert 'TEXT PAGE' in d[1].get_text()
