"""Small engine regression tests; intentionally run without the Qt UI installed."""
import ast
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def engine_exports():
    """Load only non-Qt engine functions from the single-file v0.5 codebase."""
    tree = ast.parse((ROOT / 'main.py').read_text())
    names = {'execute', 'unique_path', 'ensure_tool', 'run_command', 'parse_pages'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = {'Path':Path, 'tempfile':tempfile, 'shutil':shutil, 'subprocess':subprocess,
                 'fitz':fitz, 'Image':Image, 'zipfile':zipfile}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'engine_functions', 'exec'), namespace)
    return namespace

class Progress:
    def __init__(self):
        self.values = []
    def emit(self, value):
        self.values.append(value)

def sample_pdf(path, pages=3):
    with fitz.open() as doc:
        for index in range(pages):
            page = doc.new_page(width=280, height=360)
            page.insert_text((50, 65), f'Page {index+1}')
        doc.save(str(path))

def test_pdf_multi_page_png_zipped(tmp_path):
    engine = engine_exports()
    input_pdf = tmp_path / 'sample.pdf'
    sample_pdf(input_pdf, 3)
    progress = Progress()
    outputs = engine['execute']('pdf_png_zip',[str(input_pdf)],str(tmp_path), progress)
    assert len(outputs) == 1 and outputs[0].suffix == '.zip'
    with zipfile.ZipFile(outputs[0]) as archive:
        assert archive.namelist() == ['Page_001.png', 'Page_002.png', 'Page_003.png']
        assert archive.read('Page_001.png').startswith(b'\x89PNG')
    assert progress.values[-1] == 100

def test_pdf_multi_page_jpg_zipped(tmp_path):
    engine = engine_exports()
    input_pdf = tmp_path / 'sample.pdf'
    sample_pdf(input_pdf, 2)
    outputs = engine['execute']('pdf_jpg_zip',[str(input_pdf)],str(tmp_path), Progress())
    with zipfile.ZipFile(outputs[0]) as archive:
        assert archive.namelist() == ['Page_001.jpg', 'Page_002.jpg']
        assert archive.read('Page_001.jpg').startswith(b'\xff\xd8\xff')

def test_single_page_png_is_direct_file(tmp_path):
    engine = engine_exports()
    p = tmp_path / 'one.pdf'
    sample_pdf(p, 1)
    result = engine['execute']('pdf_png_zip',[str(p)],str(tmp_path),Progress())
    assert result[0].suffix == '.png'
    assert result[0].read_bytes().startswith(b'\x89PNG')

def test_multiple_pdfs_merged(tmp_path):
    engine = engine_exports()
    a, b = tmp_path / 'a.pdf', tmp_path / 'b.pdf'
    sample_pdf(a, 2)
    sample_pdf(b, 3)
    output = engine['execute']('merge_pdf',[str(a),str(b)],str(tmp_path),Progress())
    with fitz.open(output[0]) as merged:
        assert len(merged) == 5


def test_images_into_pdf(tmp_path):
    engine = engine_exports()
    a, b = tmp_path / 'a.png', tmp_path / 'b.png'
    Image.new('RGB', (50, 80), 'blue').save(a)
    Image.new('RGB', (50, 80), 'green').save(b)
    output = engine['execute']('images_pdf',[str(a),str(b)],str(tmp_path),Progress())
    with fitz.open(output[0]) as merged:
        assert len(merged) == 2
