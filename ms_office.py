"""Windows: convert with Microsoft Office itself when it is installed.

PowerPoint/Word/Excel export their own files to PDF far faster than
LibreOffice (a large presentation: seconds instead of minutes) and with exact
fidelity. Used only on Windows and only for a plain PDF export; anything that
fails here falls back to LibreOffice.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

APPS = {
    '.ppt': 'PowerPoint.Application', '.pptx': 'PowerPoint.Application',
    '.pps': 'PowerPoint.Application', '.ppsx': 'PowerPoint.Application',
    '.doc': 'Word.Application', '.docx': 'Word.Application', '.rtf': 'Word.Application',
    '.xls': 'Excel.Application', '.xlsx': 'Excel.Application', '.xlsm': 'Excel.Application',
}
TIMEOUT = 240  # seconds; a stuck Office (e.g. an activation prompt) falls back to LibreOffice


def _installed(progid):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + '\\CLSID'):
            return True
    except OSError:
        return False


def available(suffix):
    if sys.platform != 'win32':
        return False
    progid = APPS.get(suffix.lower())
    return bool(progid) and _installed(progid)


def _export(progid, source, target):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = None
    quit_after = True
    try:
        app = win32com.client.DispatchEx(progid)
        if progid.startswith('PowerPoint'):
            # PowerPoint runs as a single instance: if the user already has
            # presentations open, do not close their PowerPoint afterwards.
            try:
                quit_after = app.Presentations.Count == 0
            except Exception:
                quit_after = False
            # msoTrue/msoFalse = -1/0. WithWindow=False keeps it invisible.
            pres = app.Presentations.Open(source, -1, 0, 0)  # ReadOnly, Untitled, WithWindow
            try:
                pres.SaveAs(target, 32)  # ppSaveAsPDF
            finally:
                pres.Close()
        elif progid.startswith('Word'):
            app.Visible = False
            app.DisplayAlerts = 0
            doc = app.Documents.Open(source, False, True, False)  # ConfirmConversions, ReadOnly, AddToRecent
            try:
                doc.ExportAsFixedFormat(target, 17)  # wdExportFormatPDF
            finally:
                doc.Close(0)
        else:
            app.Visible = False
            app.DisplayAlerts = False
            book = app.Workbooks.Open(source, 0, True)  # UpdateLinks, ReadOnly
            try:
                book.ExportAsFixedFormat(0, target)  # xlTypePDF
            finally:
                book.Close(False)
    finally:
        if app is not None and quit_after:
            try:
                app.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def to_pdf(source, target):
    """Export `source` to the PDF `target`. Raises on any problem."""
    source, target = str(Path(source).resolve()), str(Path(target).resolve())
    progid = APPS[Path(source).suffix.lower()]
    result = {}

    def run():
        try:
            _export(progid, source, target)
        except BaseException as exc:  # reported to the caller
            result['error'] = exc

    worker = threading.Thread(target=run, name='Morphix MS Office export', daemon=True)
    worker.start()
    worker.join(TIMEOUT)
    if worker.is_alive():
        raise TimeoutError(f'Microsoft Office did not finish within {TIMEOUT} s')
    if 'error' in result:
        raise result['error']
    if not Path(target).is_file() or Path(target).stat().st_size == 0:
        raise RuntimeError('Microsoft Office produced no PDF')
    return Path(target)
