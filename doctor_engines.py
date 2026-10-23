"""Print which Morphix backends are ready (no GUI required)."""
from pathlib import Path
from core_ops import find_rar_writer
from office_engine import find_office_engine
from ocr_engine import find_tessdata

if __name__ == '__main__':
    print('Morphix engine status')
    print('---------------------')
    try:
        import pymupdf
        print('PDF engine:         READY (PyMuPDF)')
    except ImportError:
        print('PDF engine:         MISSING (pip install -r requirements.txt)')
    data = find_tessdata()
    print('Arabic+English OCR: READY' if data else 'Arabic+English OCR: MISSING language data')
    if data:
        print('  OCR data:', data)
    office = find_office_engine()
    print('Office → PDF:       READY' if office else 'Office → PDF:       MISSING LibreOffice runtime')
    if office:
        print('  Office engine:', office)
    rar = find_rar_writer()
    print('RAR creation:       READY (licensed writer)' if rar else 'RAR creation:       UNAVAILABLE; licensed writer required')
    print('ZIP/TAR.GZ:         READY (standard library)')
