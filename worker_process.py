"""Subprocess conversion worker, isolated from the Morphix Qt GUI process.

A native crash in PyMuPDF, FFmpeg, or OCR then terminates the worker rather
than the Quick Wheel or Studio. Protocol: newline-delimited JSON, prefixed.
"""
import json
import os
import sys
import traceback
from pathlib import Path

import win_compat  # noqa: F401

PREFIX = 'MORPHIX_EVENT='


def send(kind, **data):
    print(PREFIX + json.dumps({'type': kind, **data}, ensure_ascii=False), flush=True)


class Progress:
    def emit(self, value):
        send('progress', value=int(value))

    def status(self, text):
        send('status', text=str(text))


def worker_main(request_file):
    try:
        request = json.loads(Path(request_file).read_text(encoding='utf-8'))
        # No QApplication, dialogs or GUI instances are created in this process.
        from engine_core import execute
        results = execute(request['action'], request['paths'], request['out_dir'],
                          Progress(), request.get('options') or {})
        send('completed', outputs=[str(x) for x in results])
        return 0
    except BaseException:
        trace = traceback.format_exc()
        send('failed', message=trace[-6000:])
        return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        send('failed', message='Expected one request JSON filename')
        sys.exit(2)
    sys.exit(worker_main(sys.argv[1]))
