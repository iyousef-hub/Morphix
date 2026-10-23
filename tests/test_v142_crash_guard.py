"""Regression tests for subprocess isolation; do not require PySide6."""
import ast
import json
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'MORPHIX_EVENT='


def run_job(tmp_path, action, inputs):
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'action': action, 'paths': [str(p) for p in inputs],
                                   'out_dir': str(tmp_path), 'options': {}}, ensure_ascii=False))
    result = subprocess.run([sys.executable, '-u', str(ROOT / 'worker_process.py'), str(request)],
                            capture_output=True, text=True, timeout=25)
    events = [json.loads(line[len(PREFIX):]) for line in result.stdout.splitlines()
              if line.startswith(PREFIX)]
    return result, events


def test_headless_worker_creates_pdf_and_reports_progress(tmp_path):
    image = tmp_path / 'sample.png'
    Image.new('RGB', (128, 80), 'royalblue').save(image)
    process, events = run_job(tmp_path, 'images_pdf', [image])
    assert process.returncode == 0, process.stderr
    assert any(e['type'] == 'progress' for e in events)
    output = Path([e for e in events if e['type'] == 'completed'][0]['outputs'][0])
    with fitz.open(output) as pdf:
        assert len(pdf) == 1


def test_headless_worker_reports_error_without_exiting_app(tmp_path):
    image = tmp_path / 'sample.png'
    Image.new('RGB', (10, 10)).save(image)
    process, events = run_job(tmp_path, 'invalid_action', [image])
    assert process.returncode == 1
    assert any(e['type'] == 'failed' and 'Unsupported action' in e['message'] for e in events)


def test_gui_calls_conversion_job_instead_of_qthread():
    main = (ROOT / 'main.py').read_text()
    wheel = (ROOT / 'quickwheel.py').read_text()
    for src in (main, wheel):
        ast.parse(src)
        assert 'ConversionJob(' in src
        assert 'QThread(' not in src
        assert 'moveToThread(' not in src
    ast.parse((ROOT / 'engine_core.py').read_text())
    assert 'from main import' not in (ROOT / 'worker_process.py').read_text()


def test_engine_failure_does_not_load_qt():
    source = (ROOT / 'engine_core.py').read_text()
    assert 'PySide6' not in source
    assert 'QApplication' not in source
