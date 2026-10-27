"""Qt-safe external conversion job; GUI never runs native converters in QThreads."""
import json
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

PREFIX = 'MORPHIX_EVENT='



def _tr(text):
    try:
        from i18n import tr
        return tr(text)
    except Exception:
        return text


class ConversionJob(QObject):
    progress = Signal(int)
    status = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, action, paths, out_dir, options=None, parent=None):
        super().__init__(parent)
        self.action, self.paths = action, list(paths)
        self.out_dir, self.options = str(out_dir), (options or {})
        self._output_buffer = ''
        self._stderr_tail = ''
        self._result = None
        self._failure = None
        self._done = False
        self._cancelled = False
        self._request_path = None
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._on_error)

    def start(self):
        fd, self._request_path = tempfile.mkstemp(prefix='morphix-task-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                try:
                    import i18n
                    self.options.setdefault('ui_lang', i18n.current())
                except Exception:
                    pass
                json.dump({'action': self.action, 'paths': self.paths,
                           'out_dir': self.out_dir, 'options': self.options}, f, ensure_ascii=False)
            if getattr(sys, 'frozen', False):
                # PyInstaller one-dir GUI executable can dispatch worker mode.
                program = sys.executable
                args = ['--morphix-worker', self._request_path]
            else:
                program = sys.executable
                args = ['-u', str(Path(__file__).with_name('worker_process.py')),
                        self._request_path]
            self.process.start(program, args)
        except Exception:
            self._remove_request()
            raise

    def _read_stdout(self):
        self._output_buffer += bytes(self.process.readAllStandardOutput()).decode('utf-8', 'replace')
        while '\n' in self._output_buffer:
            line, self._output_buffer = self._output_buffer.split('\n', 1)
            if not line.startswith(PREFIX):
                continue
            try:
                event = json.loads(line[len(PREFIX):])
                if event.get('type') == 'progress':
                    self.progress.emit(int(event.get('value', 0)))
                elif event.get('type') == 'status':
                    self.status.emit(_tr(str(event.get('text', ''))))
                elif event.get('type') == 'completed':
                    self._result = event.get('outputs', [])
                elif event.get('type') == 'failed':
                    self._failure = str(event.get('message', 'Conversion failed'))
            except (ValueError, TypeError):
                pass

    def _read_stderr(self):
        self._stderr_tail = (self._stderr_tail + bytes(
            self.process.readAllStandardError()).decode('utf-8', 'replace'))[-3500:]

    def _on_error(self, error):
        if error == QProcess.FailedToStart:
            self._failure = 'Conversion process failed to start: ' + self.process.errorString()
            self._finish_once(False)

    def _finished(self, exit_code, status):
        self._read_stdout()
        self._read_stderr()
        success = (status == QProcess.NormalExit and exit_code == 0 and
                   self._result is not None and self._failure is None)
        if self._cancelled:
            self._failure = 'Cancelled.'
            success = False
        elif not success and not self._failure:
            self._failure = (f'Conversion engine stopped unexpectedly (code {exit_code}; '
                             f'status {status}). The Morphix app is still running.\n'
                             f'{self._stderr_tail}')
        self._finish_once(success)

    def _remove_request(self):
        if self._request_path:
            try:
                os.unlink(self._request_path)
            except OSError:
                pass
            self._request_path = None

    def _finish_once(self, success):
        if self._done:
            return
        self._done = True
        self._remove_request()
        if success:
            self.completed.emit(self._result)
        else:
            self.failed.emit((self._failure or 'Conversion process failed')[-4500:])
        self.finished.emit()

    def cancel(self):
        """User cancel. Long transcriptions keep a checkpoint and resume later."""
        self._cancelled = True
        self.stop()

    def stop(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(2000):
                self.process.kill()
                self.process.waitForFinished(1000)
        self._remove_request()
