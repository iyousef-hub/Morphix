from pathlib import Path
import io
import sys
import zipfile
import fitz
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_intelligence import selection_profile, file_summary, category_for
from core_ops import archive_files, extract_pdf_text
from test_engine import engine_exports, Progress


def test_content_sniff_and_summary(tmp_path):
    pdfs = []
    for i in range(6):
        p=tmp_path/f'doc{i}.pdf'; p.write_bytes(b'%PDF-1.4 fake body'); pdfs.append(str(p))
    pngs=[]
    for i in range(2):
        p=tmp_path/f'i{i}.png'; Image.new('RGB',(3,3)).save(p); pngs.append(str(p))
    jpeg=tmp_path/'j.jpeg'; Image.new('RGB',(3,3)).save(jpeg)
    paths=pdfs+pngs+[str(jpeg)]
    assert selection_profile(pdfs)=='pdf_multi'
    assert selection_profile(pngs)=='image_multi'
    assert selection_profile(paths)=='pdf_image_mix'
    assert file_summary(paths)==['6 PDF','2 PNG','1 JPEG']
    mislabeled=tmp_path/'hello.tmp'; Image.new('RGB',(3,3)).save(mislabeled,format='PNG')
    assert category_for(mislabeled)=='image'


def test_context_offers_merge_for_pdf_plus_images_but_not_other_mixed(tmp_path):
    from ast import parse, FunctionDef, Module
    import ast
    tree=parse((Path(__file__).parents[1]/'main.py').read_text())
    funcs=[node for node in tree.body if isinstance(node,FunctionDef) and node.name in ('supported_actions','_supported_base')]
    ns={'Path':Path}
    exec(compile(Module(body=funcs, type_ignores=[]), 'main_actions', 'exec'),ns)
    pdf=tmp_path/'p.pdf';pdf.write_bytes(b'%PDF-1.4 hello')
    img=tmp_path/'q.png';Image.new('RGB',(2,2)).save(img)
    assert ns['supported_actions']([str(pdf),str(img)])==['merge_pdf','merge_optimize','zip_files','tar_gz_files','rar_files']
    other=tmp_path/'track.mp3';other.write_bytes(b'fake')
    assert ns['supported_actions']([str(pdf),str(other)])==['zip_files','tar_gz_files','rar_files']
    single=ns['supported_actions']([str(pdf)])
    assert 'extract_pdf_text' in single and 'pdf_png_zip' in single
    multi=ns['supported_actions']([str(pdf),str(pdf)])
    assert 'merge_pdf' in multi and 'zip_files' in multi


def test_archive_handles_duplicate_names_from_different_folders(tmp_path):
    a,b=tmp_path/'one',tmp_path/'two';a.mkdir();b.mkdir()
    (a/'report.pdf').write_bytes(b'first');(b/'report.pdf').write_bytes(b'second')
    out=archive_files([a/'report.pdf',b/'report.pdf'],tmp_path)[0]
    with zipfile.ZipFile(out) as z:
        assert z.namelist()==['report.pdf','report_2.pdf']
        assert z.read('report_2.pdf')==b'second'


def test_pdf_text_unicode_utf8(tmp_path):
    source=tmp_path/'English.pdf'
    with fitz.open() as d:
        p=d.new_page();p.insert_text((40,60),'Hello English PDF text')
        d.save(source)
    out=extract_pdf_text([source],tmp_path)[0]
    assert 'Hello English PDF text' in out.read_text(encoding='utf-8-sig')
    assert out.suffix=='.txt'


def test_scanned_pdf_warns_no_fake_text(tmp_path):
    source=tmp_path/'scan.pdf'
    with fitz.open() as d:
        p=d.new_page();d.save(source)
    with pytest.raises(ValueError,match='No text recognized'):
        extract_pdf_text([source],tmp_path)


def test_rar_is_never_fake_zip(tmp_path, monkeypatch):
    import core_ops
    monkeypatch.setattr(core_ops.shutil,'which',lambda _:None)
    sample=tmp_path/'x.txt';sample.write_text('hi')
    with pytest.raises(RuntimeError,match='licensed RAR writer'):
        archive_files([sample],tmp_path,'rar')
    assert not list(tmp_path.glob('*.rar'))


def test_image_to_pdf_actual_conversion(tmp_path):
    a,b=tmp_path/'a.png',tmp_path/'b.jpg'
    Image.new('RGB',(12,12),'red').save(a)
    Image.new('RGB',(18,8),'green').save(b)
    outputs=engine_exports()['execute']('images_pdf',[str(a),str(b)],str(tmp_path),Progress())
    with fitz.open(outputs[0]) as doc:
        assert len(doc)==2


def test_wheel_profiles_are_context_specific():
    import ast
    content=(Path(__file__).parents[1]/'quickwheel.py').read_text()
    tree=ast.parse(content)
    profiles=next(ast.literal_eval(assign.value) for assign in tree.body if isinstance(assign,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROFILES' for t in assign.targets))
    assert profiles['mixed'][1]==['zip_files','tar_gz_files','rar_files']
    assert 'merge_pdf' in profiles['pdf_image_mix'][1]
    assert len(profiles['pdf_multi'][1])<=8   # wheel shows 6; panels show up to 8-9
    assert 'merge_pdf' in profiles['pdf_multi'][1]
    assert 'images_pdf' in profiles['image_single'][1]
    assert all('more_actions' not in profiles[p][1] for p in ('mixed','audio_single','video_single'))


def test_execute_dispatches_pdf_text_and_zip(tmp_path):
    engine=engine_exports()
    p=tmp_path/'a.pdf'
    with fitz.open() as d:
        page=d.new_page()
        page.insert_text((30,40),'Real PDF text')
        d.save(p)
    txt=engine['execute']('extract_pdf_text',[str(p)],str(tmp_path),Progress())
    assert 'Real PDF text' in txt[0].read_text(encoding='utf-8-sig')
    archives=engine['execute']('zip_files',[str(p),str(txt[0])],str(tmp_path),Progress())
    with zipfile.ZipFile(archives[0]) as z:
        assert len(z.namelist())==2
