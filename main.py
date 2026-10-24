"""Morphix 1.4 — unified local-first file tool for Quick Wheel and Studio."""
import os
import sys
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from uuid import uuid4

import win_compat  # noqa: F401  (Windows: hide helper consoles, UTF-8 output)

# After a language switch the old process needs a moment to release its sockets.
if __name__ == '__main__' and '--delay-start' in sys.argv:
    import time
    try:
        time.sleep(min(5.0, float(sys.argv[sys.argv.index('--delay-start') + 1])))
    except (IndexError, ValueError):
        pass

# Validate and pin the Cocoa platform plugin before QtWidgets loads. This
# prevents the invisible Studio child from failing with a bare Qt abort when a
# new .venv lacks libqcocoa.dylib.
if __name__ == '__main__' and not getattr(sys, 'frozen', False) and '--morphix-worker' not in sys.argv:
    from runtime_guard import verify_or_relaunch
    verify_or_relaunch(Path(__file__).resolve().parent)

if sys.platform == 'darwin':
    from qt_macos_runtime import configure_qt_macos
    try:
        configure_qt_macos()
    except RuntimeError as exc:
        print('[Morphix Qt Runtime] ' + str(exc), flush=True)
        raise SystemExit(86)

from PySide6.QtCore import Qt, QObject, Signal, QEvent, QTimer, QSettings
from PySide6.QtGui import QAction, QKeyEvent, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QMenu, QMessageBox, QProgressBar, QTextEdit, QFrame, QSplitter, QInputDialog)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
import hashlib
from branding import AboutDialog, SplashDialog
from app_assets import logo_png
from i18n import tr
import i18n

APP_VERSION = '1.8.0'

PDF = {'.pdf'}
IMAGE = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
from file_intelligence import VIDEO, AUDIO  # one list for the whole app
OFFICE = {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.odp', '.ods'}

ACTIONS = {
    'visual_pdf': 'Visual PDF editor', 'visual_image': 'Visual image editor',
    'merge_pdf': 'Merge to PDF', 'merge_optimize': 'Merge to PDF + compress',
    'split_pdf': 'Extract PDF page range', 'separate_pdf': 'Separate PDF into multiple parts', 'optimize_pdf': 'Optimize PDF',
    'rotate_pdf': 'Rotate PDF 90°', 'pdf_png': 'PDF pages → PNG',
    'pdf_png_zip': 'PDF → PNG (ZIP for multi-page)', 'pdf_jpg_zip': 'PDF → JPG (ZIP for multi-page)',
    'crop_pdf': 'Crop PDF pages (margins)', 'delete_pdf_pages': 'Remove PDF pages',
    'extract_pdf_pages': 'Extract PDF page range',
    'images_pdf': 'Images → single PDF', 'image_png': 'Images → PNG',
    'image_jpg': 'Images → JPG', 'image_webp': 'Images → WebP',
    'image_resize': 'Resize images (max 1920 px)',
    'image_compress': 'Compress images (JPEG)', 'image_rotate': 'Rotate images 90°',
    'image_grayscale': 'Images → grayscale', 'image_crop': 'Crop image borders by percentage',
    'join_video': 'Join videos → MP4', 'video_mp4': 'Videos → MP4',
    'video_mp3': 'Extract audio → MP3', 'audio_mp3': 'Audio → MP3',
    'join_audio': 'Merge audio tracks → MP3',
    'office_pdf': 'Office documents → PDF',
    'zip_files': 'Create ZIP archive', 'rar_files': 'Create RAR archive (licensed engine)',
    'tar_gz_files': 'Create TAR.GZ archive',
    'extract_pdf_text': 'PDF → Extract text (auto OCR)',
    'ocr_pdf_text': 'OCR → Text file (Arabic + English)',
    'ocr_searchable_pdf': 'OCR · Make the PDF searchable',
    'ocr_image_text': 'Images → Extract text (Arabic + English OCR)',
    'transcribe_media': 'Speech → Text (Arabic / English, offline)',
    'remove_bg': 'Remove the background (keeps full quality)',
    'docs_merge_pdf': 'Merge everything into one PDF',
    'docs_pdf_each': 'Convert each file to its own PDF',
    'xlsx_pdf_fit': 'Excel → PDF (each sheet fits one page)',
    'xlsx_csv': 'Excel → CSV (one file per sheet)',
    'xlsx_split': 'Split sheets into separate Excel files',
    'xlsx_merge': 'Merge workbooks into one Excel file',
    'csv_xlsx': 'CSV → Excel',
}

def supported_actions(paths):
    """Context-aware actions, including ordered PDF + image merges."""
    if not paths:
        return []
    from file_intelligence import selection_profile
    profile = selection_profile(paths)
    if profile == 'pdf_single':
        return ['pdf_png_zip', 'pdf_jpg_zip', 'extract_pdf_text', 'ocr_pdf_text', 'ocr_searchable_pdf', 'optimize_pdf',
                'split_pdf', 'separate_pdf', 'visual_pdf', 'rotate_pdf', 'zip_files', 'rar_files',
                'crop_pdf', 'delete_pdf_pages', 'extract_pdf_pages']
    if profile == 'pdf_image_mix':
        return ['merge_pdf', 'merge_optimize', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'pdf_multi':
        return ['merge_pdf', 'merge_optimize', 'optimize_pdf', 'zip_files',
                'pdf_png_zip', 'pdf_jpg_zip', 'extract_pdf_text', 'ocr_pdf_text', 'ocr_searchable_pdf', 'rar_files',
                'rotate_pdf']
    if profile == 'image_single':
        return ['images_pdf', 'remove_bg', 'image_jpg', 'image_png', 'image_webp',
                'image_compress', 'ocr_image_text', 'visual_image', 'image_resize', 'image_rotate',
                'image_grayscale', 'image_crop', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'image_multi':
        return ['images_pdf', 'remove_bg', 'image_jpg', 'image_png', 'image_webp',
                'image_compress', 'ocr_image_text', 'image_resize', 'zip_files', 'rar_files',
                'image_rotate', 'image_grayscale', 'image_crop']
    if profile == 'video_single':
        return ['transcribe_media', 'video_mp3', 'video_mp4', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'video_multi':
        return ['transcribe_media', 'join_video', 'video_mp3', 'video_mp4', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'audio_single':
        return ['transcribe_media', 'audio_mp3', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'audio_multi':
        return ['transcribe_media', 'join_audio', 'audio_mp3', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'office':
        many = ['docs_merge_pdf'] if len(paths) > 1 else []
        return ['office_pdf', *many, 'zip_files', 'tar_gz_files', 'rar_files']
    if profile == 'docs_mix':
        return ['docs_merge_pdf', 'docs_pdf_each', 'zip_files', 'tar_gz_files', 'rar_files']
    if profile in ('excel_single', 'excel_multi'):
        csvs = [p for p in paths if str(p).lower().endswith('.csv')]
        acts = ['office_pdf', 'xlsx_pdf_fit']
        if profile == 'excel_multi':
            acts += ['docs_merge_pdf', 'xlsx_merge']
        if len(csvs) < len(paths):
            acts += ['xlsx_csv', 'xlsx_split']
        if csvs:
            acts += ['csv_xlsx']
        return acts + ['zip_files', 'tar_gz_files', 'rar_files']
    return ['zip_files', 'tar_gz_files', 'rar_files']

def parse_pages(value, total):
    result = []
    for part in value.replace(' ', '').split(','):
        if not part: continue
        bits = part.split('-')
        if len(bits) > 2: raise ValueError('Invalid page range')
        try:
            a = int(bits[0]); b = int(bits[-1])
        except ValueError: raise ValueError('Page ranges must be numbers, e.g. 1-3,5')
        if a < 1 or b > total or a > b:
            raise ValueError(f'Page range must be between 1 and {total}')
        result.extend(range(a-1, b))
    return list(dict.fromkeys(result))

def unique_path(folder, name):
    target = Path(folder) / name
    if not target.exists():
        return target
    stem, ext = target.stem, target.suffix
    n = 2
    while (Path(folder) / f'{stem}_{n}{ext}').exists():
        n += 1
    return Path(folder) / f'{stem}_{n}{ext}'

def run_command(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors='replace')
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-1500:])

def ensure_tool(name):
    if name == 'ffmpeg':
        # imageio-ffmpeg ships platform-specific FFmpeg executables in its wheels.
        # PyInstaller bundles that executable when built with the supplied spec.
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} is not available in this build.')
    return path

def execute(action, paths, out_dir, progress, options=None):
    """Single source of truth lives in engine_core (also used by the worker)."""
    from engine_core import execute as engine_execute
    return engine_execute(action, paths, out_dir, progress, options)

class DropList(QListWidget):
    paths_dropped = Signal(list)
    quick_actions_requested = Signal()
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.quick_actions_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.paths_dropped.emit([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
            event.acceptProposedAction()
        else: event.ignore()

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr('Morphix — Studio'))
        self.setWindowIcon(QIcon(logo_png()))
        self.resize(1110, 755)
        self.setMinimumSize(880, 610)
        self.setAcceptDrops(True)
        self.thread = None
        self.worker = None
        self.build_ui()
        # No application-wide event filter: it can intercept modal/shortcut input.
        self.files.quick_actions_requested.connect(self.show_actions)
    def build_ui(self):
        from studio_layout import build_studio_ui
        build_studio_ui(self)

    def open_shortcuts(self):
        if self.controller:
            self.controller.open_preferences(page=2)

    def open_quick_wheel(self):
        # Standalone Studio does not own a QuickWheelController or its monitor.
        # Instead ask the independent menu-bar/tray helper via IPC.  The old
        # call to StudioController.show_wheel raised AttributeError on every
        # click, making the entire Studio appear unresponsive.
        if getattr(self, 'controller', None):
            self.controller.open_quick_wheel()

    def open_addons(self):
        from addons import AddonsDialog
        AddonsDialog(self).exec()

    def open_speech_models(self):
        from transcription_dialog import TranscriptionDialog
        dialog = TranscriptionDialog([], self)
        dialog.setWindowTitle(tr('Morphix · Speech models'))
        dialog.start.setText(tr('Close'))
        dialog.exec()

    def reveal_outputs(self):
        outputs = getattr(self, 'last_outputs', [])
        if not outputs:
            return
        import subprocess
        if sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', outputs[0]])
        elif os.name == 'nt':
            subprocess.Popen(['explorer', '/select,', outputs[0]])
        else:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(outputs[0]).parent)))

    def open_language(self):
        if self.controller:
            self.controller.open_preferences(page=5)

    def open_wheel_settings(self):
        if self.controller:
            self.controller.open_preferences()

    def focus_files(self, paths):
        """Add files from Quick Wheel to Studio and target just those files."""
        self.append_files(paths)
        wanted = {str(Path(p).resolve()) for p in paths}
        for i in range(self.files.count()):
            item = self.files.item(i)
            item.setSelected(item.data(Qt.UserRole) in wanted)
        self.refresh_actions()

    def append_files(self, paths):
        existing = {self.files.item(i).data(Qt.UserRole) for i in range(self.files.count())}
        for path in paths:
            p = str(Path(path).resolve())
            if Path(p).is_file() and p not in existing:
                item = QListWidgetItem('▣   ' + Path(p).name)
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                self.files.addItem(item); existing.add(p)
        self.refresh_actions()
    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Choose files'))
        self.append_files(paths)
    def remove_selected(self):
        for item in self.files.selectedItems(): self.files.takeItem(self.files.row(item))
        self.refresh_actions()
    def clear_files(self):
        self.files.clear(); self.refresh_actions()
    def selected_paths(self):
        chosen = self.files.selectedItems()
        if not chosen:
            chosen = [self.files.item(i) for i in range(self.files.count())]
        return [i.data(Qt.UserRole) for i in chosen]
    def refresh_actions(self):
        self.count.setText(tr('{n} files', n=self.files.count()))
        while self.action_box.count():
            it = self.action_box.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        acts = supported_actions(self.selected_paths())
        if hasattr(self, 'empty_hint'):
            self.empty_hint.setVisible(self.files.count() == 0)
        self.hint.setText(tr('Choose a tool. Select some files in the list to work on them only.') if acts else
                          tr('Add files to see the tools that fit them.'))
        from studio_layout import action_button
        for key in acts:
            btn = action_button(key, tr(ACTIONS[key]))
            btn.setEnabled(self.thread is None)
            btn.clicked.connect(lambda _checked=False, k=key: self.start_action(k))
            self.action_box.addWidget(btn)
        self.action_box.addStretch()
    def show_actions(self):
        acts = supported_actions(self.selected_paths())
        if not acts: return
        menu = QMenu(self)
        for key in acts:
            act = QAction(i18n.amp(tr(ACTIONS[key])), self)
            act.triggered.connect(lambda _checked=False, k=key: self.start_action(k))
            menu.addAction(act)
        menu.exec(self.cursor().pos())
    def start_action(self, key):
        if self.thread is not None: return
        paths = self.selected_paths()
        if key not in supported_actions(paths): return
        if key in ('visual_pdf', 'visual_image'):
            from visual_editor import PdfEditor, ImageEditor
            try:
                dialog = PdfEditor(paths[0], self) if key == 'visual_pdf' else ImageEditor(paths[0], self)
                dialog.exec()
            except Exception as exc:
                QMessageBox.warning(self, tr('Morphix · Editor unavailable'), str(exc))
            return
        if (key in ('merge_pdf', 'merge_optimize', 'images_pdf', 'docs_merge_pdf', 'xlsx_merge') and len(paths) > 1):
            from merge_order_dialog import ask_merge_order
            paths = ask_merge_order(paths, parent=self)
            if paths is None:
                return
        options = {}
        if key in ('split_pdf', 'separate_pdf'):
            from range_dialogs import ask_pdf_ranges
            ranges = ask_pdf_ranges(paths, separate=key == 'separate_pdf', parent=self)
            if ranges is None: return
            options['page_ranges'] = ranges
        elif key in ('delete_pdf_pages', 'extract_pdf_pages'):
            pages, ok = QInputDialog.getText(self, tr('Choose pages'), tr('Pages (for example 1-3, 5):'))
            if not ok or not pages.strip(): return
            options['pages'] = pages.strip()
        elif key in ('crop_pdf', 'image_crop'):
            percent, ok = QInputDialog.getInt(self, tr('Crop'), tr('How much to trim from each edge (%):'), 5 if key == 'crop_pdf' else 10, 1, 45)
            if not ok: return
            options['margin_percent' if key == 'crop_pdf' else 'crop_percent'] = percent
        elif key in ('image_compress', 'optimize_pdf', 'merge_optimize'):
            from compression_dialog import CompressionDialog
            dialog = CompressionDialog(paths, 'image' if key == 'image_compress' else 'pdf', self)
            if not dialog.exec(): return
            options.update(dialog.options())
        elif key == 'remove_bg':
            from background_dialog import ask_background_options
            chosen = ask_background_options(paths, parent=self)
            if chosen is None: return
            options.update(chosen)
        elif key == 'transcribe_media':
            from transcription_dialog import ask_transcription_options
            chosen = ask_transcription_options(paths, parent=self)
            if chosen is None: return
            options.update(chosen)
        elif key == 'image_resize':
            pixels, ok = QInputDialog.getInt(self, tr('Resize images'), tr('Longest side (pixels):'), 1920, 64, 16000)
            if not ok: return
            options['max_pixels'] = pixels
        folder = QFileDialog.getExistingDirectory(self, tr('Where should the results be saved?'))
        if not folder: return
        self.progress.setValue(0)
        self.status.setPlainText(tr('Working on: {task}…', task=tr(ACTIONS[key])))
        from conversion_job import ConversionJob
        self.thread = ConversionJob(key, paths, folder, options, parent=self)
        self.worker = None  # conversion runs in a child process, not a Qt thread
        self.thread.progress.connect(self.progress.setValue)
        self.thread.status.connect(lambda text: self.status.setPlainText(text))
        self.thread.completed.connect(self.done)
        self.thread.failed.connect(self.failed)
        self.thread.finished.connect(self.cleanup)
        self.thread.start()
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setVisible(True)
        self.refresh_actions()
    def cancel_action(self):
        if self.thread is not None:
            self.thread.cancel()
    def done(self, outputs):
        self.progress.setValue(100)
        self.status.setPlainText('✓ ' + tr('{n} file(s) created:', n=len(outputs)) + '\n' + '\n'.join(str(p) for p in outputs[:6]))
        self.last_outputs = [str(p) for p in outputs]
        if hasattr(self, 'reveal_button'):
            self.reveal_button.setVisible(bool(outputs))
    def failed(self, error):
        if error.strip() == 'Cancelled.':
            self.status.setPlainText(tr('Cancelled. Speech → Text continues where it stopped next time you run it on the same file.'))
            return
        self.status.setPlainText(tr('Something went wrong:') + ' ' + _friendly_error(error))
        QMessageBox.warning(self, tr('Morphix · The task could not be completed'), _friendly_error(error))
    def cleanup(self):
        job = self.thread
        self.worker = None; self.thread = None
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setVisible(False)
        if job is not None:
            job.deleteLater()
        self.refresh_actions()
    def hideEvent(self, event):
        super().hideEvent(event)
        # Minimizing sends a *spontaneous* hide event; it must not quit Studio.
        if event.spontaneous() or self.isMinimized():
            return
        if self.thread is not None:
            return
        if getattr(self, 'controller', None):
            QTimer.singleShot(0, self.controller.on_studio_hidden)

    def closeEvent(self, event):
        if self.thread is not None:
            answer = QMessageBox.question(
                self, tr('Morphix · A task is running'),
                tr('A task is still running. Cancel it and close Studio?\n\n'
                   'Speech → Text keeps its progress and continues next time.'))
            if answer == QMessageBox.Yes:
                self.thread.cancel()
                QTimer.singleShot(0, self.close)
            event.ignore()
        else:
            event.accept()
            if self.controller:
                QTimer.singleShot(0, self.controller.on_studio_hidden)

def _friendly_error(text):
    """Show the exception message of a worker traceback, not the whole stack."""
    import re
    text = (text or '').strip()
    if 'Traceback (most recent call last)' not in text:
        return text[-1500:]
    lines = text.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        m = re.match(r'^[A-Za-z_][\w.]*(Error|Exception|Exit|Interrupt): ?(.*)$', lines[i])
        if m:
            return '\n'.join([m.group(2)] + lines[i + 1:]).strip()[-1500:]
    return lines[-1][-1500:]


def _instance_socket_name():
    """Stable per-user name, shared between copies in different directories."""
    identity = str(Path.home().resolve()).encode('utf-8')
    return 'morphix-one-' + hashlib.sha256(identity).hexdigest()[:18]


def _forward_to_running_instance(name, command):
    """Ask an existing Morphix to open its window instead of spawning a wheel."""
    client = QLocalSocket()
    client.connectToServer(name)
    if not client.waitForConnected(350):
        return False
    client.write(command.encode('utf-8'))
    client.flush()
    client.waitForBytesWritten(350)
    client.disconnectFromServer()
    return True


def _hub_files_from_argv():
    """`Morphix --hub FILE…` (right-click → Morphix on Linux): the files to open in the Action Hub."""
    if '--hub' not in sys.argv:
        return []
    files = []
    for arg in sys.argv[sys.argv.index('--hub') + 1:]:
        if arg.startswith('--'):
            break
        if arg.startswith('file://'):
            from urllib.parse import unquote, urlparse
            arg = unquote(urlparse(arg).path)
        if Path(arg).is_file():
            files.append(str(Path(arg).resolve()))
    return files[:2000]


def _single_instance_server(app):
    """Enforce one Morphix GUI across ALL unpacked Morphix folders.

    Qt local sockets are per-user here. On repeated launches, forward a request
    to the existing process; stale sockets are removed only after verifying no
    app accepts a connection.
    """
    name = _instance_socket_name()
    args = set(sys.argv[1:])
    hub_files = _hub_files_from_argv()
    if hub_files:
        import json
        command = 'wheel-paths:' + json.dumps(hub_files)
    elif '--hotkey' in args:
        command = 'hotkey'
    else:
        command = ('settings' if '--settings' in args else
                   'wheel' if '--test-wheel' in args else
                   'noop' if '--background' in args or '--hub' in args else 'studio')
    if _forward_to_running_instance(name, command):
        if command.startswith('wheel-paths:') or command in ('hotkey', 'studio', 'settings'):
            print('[Morphix] Sent to the running Morphix.', flush=True)
        else:
            print('[Morphix] Another background helper owns the per-user socket. Quit ALL older Morphix helpers before launching this folder.', flush=True)
        return None
    server = QLocalServer(app)
    if not server.listen(name):
        # If another instance started at precisely the same time, don't remove
        # its live socket. Attempt forwarding first, then remove stale sockets.
        if _forward_to_running_instance(name, command):
            print('[Morphix] Another Morphix instance owns the socket; stop it before testing the updated helper.', flush=True)
            return None
        QLocalServer.removeServer(name)
        if not server.listen(name):
            print('[Morphix] Cannot acquire single-instance socket:', server.errorString(), flush=True)
            return None
    return server


if __name__ == '__main__':
    if '--morphix-worker' in sys.argv:
        from worker_process import worker_main
        ix = sys.argv.index('--morphix-worker')
        if ix + 1 >= len(sys.argv):
            sys.exit(2)
        sys.exit(worker_main(sys.argv[ix + 1]))
    # Full Morphix: launch normally with `python main.py` or the packaged app.
    # Quick Wheel imports the engine through `main`; share this module rather than
    # loading the same source twice (as both __main__ and main).
    sys.modules.setdefault('main', sys.modules[__name__])
    from quickwheel import QuickWheelController
    from PySide6.QtWidgets import QSystemTrayIcon

    app = QApplication(sys.argv)
    app.setApplicationName('Morphix')
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName('Yousef Alghamdi')
    app.setWindowIcon(QIcon(logo_png()))
    i18n.ensure_language(app)
    if '--studio-window' in sys.argv:
        # A SEPARATE normal desktop process: Qt receives clicks without
        # switching AppKit's activation policy on a live accessory process.
        from studio_host import studio_socket_name, decode_studio_message, StudioController
        app.setQuitOnLastWindowClosed(True)
        server = QLocalServer(app)
        name = studio_socket_name()
        if not server.listen(name):
            # Another Studio is already open: ask it to raise its window.
            from studio_host import send_to_studio
            if send_to_studio():
                sys.exit(0)
            QLocalServer.removeServer(name)
            if not server.listen(name):
                print('[Morphix Studio] Cannot register Studio IPC:', server.errorString(), flush=True)
                sys.exit(1)
        win = Window()
        win.controller = StudioController(win)
        def on_studio_ipc():
            while server.hasPendingConnections():
                sock = server.nextPendingConnection()
                def receive(s=sock):
                    data = bytes(s.readAll())
                    try:
                        command, page, paths = decode_studio_message(data)
                        if paths:
                            win.focus_files(paths)
                        from studio_host import bring_to_front
                        bring_to_front(win)
                        if command == 'preferences':
                            QTimer.singleShot(100, lambda p=page: win.controller.open_preferences(p))
                    except (ValueError, UnicodeDecodeError) as exc:
                        print('[Morphix Studio] IPC:', exc, flush=True)
                sock.readyRead.connect(receive)
                sock.disconnected.connect(sock.deleteLater)
                if sock.bytesAvailable():
                    receive()
        server.newConnection.connect(on_studio_ipc)
        print('[Morphix Studio] Separate process started. No background hotkey or wheel event monitors.', flush=True)
        if '--initial-paths' in sys.argv:
            idx = sys.argv.index('--initial-paths')
            try:
                import json
                selected = json.loads(sys.argv[idx+1])
                if isinstance(selected, list) and all(isinstance(p, str) for p in selected):
                    win.focus_files([p for p in selected if Path(p).is_file()])
            except (IndexError, ValueError) as exc:
                print('[Morphix Studio] Initial paths:', exc, flush=True)
        if '--studio-preferences' in sys.argv:
            idx = sys.argv.index('--studio-preferences')
            try:
                page = int(sys.argv[idx+1])
                if 0 <= page <= 10:
                    QTimer.singleShot(200, lambda p=page: win.controller.open_preferences(p))
            except (IndexError, ValueError):
                pass
        from studio_host import bring_to_front
        bring_to_front(win)
        sys.exit(app.exec())

    app.setQuitOnLastWindowClosed(False)  # background helper remains alive
    from desktop_presence import set_studio_visible
    set_studio_visible(False)  # accessory/background: no Dock icon while Studio closed
    instance_server = _single_instance_server(app)
    if instance_server is None:
        sys.exit(0)  # another copy owns the wheel; do not make a second one
    if not ({'--background', '--hub', '--hotkey'} & set(sys.argv)):
        SplashDialog().exec()  # branded splash only on manual launch
    if sys.platform.startswith('linux'):
        try:
            import linux_integration
            linux_integration.install()
        except Exception as exc:
            print('[Morphix] Linux desktop integration failed:', exc, flush=True)
    # Start with the computer by default (once). The user can turn it off in
    # Settings → Startup & background.
    _prefs = QSettings('Morphix', 'Morphix')
    if not _prefs.value('autostart_initialized', False, type=bool):
        try:
            from autostart import set_enabled
            set_enabled(True)
        except Exception as exc:
            print('[Morphix] Could not enable start at login:', exc, flush=True)
        _prefs.setValue('autostart_initialized', True)
    win = Window()
    controller = QuickWheelController(app, win)
    controller.instance_server = instance_server
    win.controller = controller

    def _handle_instance_message():
        while instance_server.hasPendingConnections():
            socket = instance_server.nextPendingConnection()
            def _read_command(sock=socket):
                command = bytes(sock.readAll()).decode('utf-8', 'replace').strip()
                if command == 'noop':
                    pass
                elif command == 'wheel':
                    QTimer.singleShot(0, controller.test_wheel)
                elif command == 'hotkey':
                    # Linux desktop keyboard shortcut (Wayland) runs `Morphix --hotkey`.
                    QTimer.singleShot(0, controller.hotkey_triggered.emit)
                elif command == 'settings':
                    QTimer.singleShot(0, controller.open_preferences)
                elif command == 'restart':
                    QTimer.singleShot(0, controller.restart_for_language)
                elif command == 'reload-settings':
                    QTimer.singleShot(0, controller.apply_appearance)
                    QTimer.singleShot(10, controller.register_shortcut)
                elif command.startswith('wheel-paths:'):
                    import json
                    try:
                        selected = json.loads(command[len('wheel-paths:'):])
                        if isinstance(selected, list) and len(selected) <= 2000:
                            selected = [p for p in selected if isinstance(p, str) and Path(p).is_file()]
                            if selected:
                                QTimer.singleShot(0, lambda files=selected: controller.show_wheel(paths_override=files))
                    except ValueError as exc:
                        print('[Morphix] Invalid Studio wheel path request:', exc, flush=True)
                else:
                    QTimer.singleShot(0, controller.open_studio)
            socket.readyRead.connect(_read_command)
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable():
                _read_command()

    instance_server.newConnection.connect(_handle_instance_message)

    # The language is chosen in Studio (a separate process). If the saved
    # choice no longer matches this background helper, restart it so the
    # Action Hub and tray menu follow the Studio language.
    def _sync_language():
        saved = i18n.chosen()
        if saved and saved != i18n.current() and controller.thread is None:
            print(f'[Morphix] Language changed to {saved}; restarting the background helper.', flush=True)
            language_timer.stop()
            controller.restart_for_language()
    language_timer = QTimer(app)
    language_timer.setInterval(3000)
    language_timer.timeout.connect(_sync_language)
    language_timer.start()
    # The old v0.8.2 only displayed its welcome once, based on persistent
    # QSettings inherited from earlier releases. On subsequent explicit runs
    # the user got ONLY a Dock icon and a hotkey line, which looked like a hang.
    # Always provide a visible entry point on interactive startup; reserve
    # silent startup for the explicit --background flag (login-item use).
    win.hide()

    def show_initial_ui():
        args = set(sys.argv[1:])
        hub_files = _hub_files_from_argv()
        if hub_files:
            controller.show_wheel(paths_override=hub_files)
        elif '--hotkey' in args:
            controller.hotkey_triggered.emit()
        elif '--studio' in args:
            print('[Morphix] Opening Studio (--studio)', flush=True)
            controller.open_studio()
        elif '--settings' in args:
            print('[Morphix] Opening Quick Wheel Settings (--settings)', flush=True)
            controller.open_preferences()
        elif '--test-wheel' in args:
            print('[Morphix] Starting Quick Wheel test (--test-wheel)', flush=True)
            controller.test_wheel()
        elif '--background' in args:
            print('[Morphix] Background mode active. Use the menu-bar M or global shortcut.', flush=True)
        elif '--welcome' in args:
            controller.show_welcome()
        else:
            print('[Morphix] Quiet background launch. Use the Quick Wheel shortcut or M tray icon.', flush=True)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print('[Morphix] Menu bar/tray unavailable; opening Studio.', flush=True)
        QTimer.singleShot(200, controller.open_studio)
    else:
        QTimer.singleShot(250, show_initial_ui)
    sys.exit(app.exec())
