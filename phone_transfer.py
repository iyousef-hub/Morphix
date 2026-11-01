"""Phone → computer over the local Wi-Fi (Morphix 1.10).

While the window is open, Morphix serves one small web page on this computer's local
network address. The phone scans the QR code, opens the page in its browser (no app),
takes photos or picks files, and they arrive here. Nothing goes through the internet.

Quality: files arrive byte-for-byte as the phone hands them over (no re-encoding here),
in 8 MB pieces that resume after a Wi-Fi hiccup, with their original date. On iPhone the
page explains how to keep originals (photo picker → Options → Format → Current).

Safety: the address carries a random key; the page only exists while the window is
open; names are made safe, free disk space is checked and nothing is overwritten.
"""
from __future__ import annotations

import base64
import html
import json
import re
import os
import secrets
import shutil
import time
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

MAX_FILE = 64 * 1024 ** 3         # 64 GB per file (long 4K videos)
CHUNK = 8 * 1024 * 1024           # the phone sends 8 MB at a time
PORTS = list(range(47820, 47840))


def default_folder():
    base = Path.home() / 'Downloads'
    if not base.is_dir():
        base = Path.home()
    return base / 'Morphix from phone' / datetime.now().strftime('%Y-%m-%d')


def safe_name(name):
    name = unquote(str(name or '')).replace('\\', '/').split('/')[-1]
    name = re.sub(r'[\x00-\x1f<>:"|?*]', '_', name).strip(' .')
    if not name:
        name = 'photo.jpg'
    if len(name) > 150:
        stem, dot, ext = name.rpartition('.')
        name = (stem[:140] + dot + ext) if dot else name[:150]
    return name


def unique(folder, name):
    dest = Path(folder) / name
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for i in range(2, 10000):
        cand = dest.with_name(f'{stem} ({i}){suffix}')
        if not cand.exists():
            return cand
    raise OSError('Too many files with the same name.')


# --------------------------------------------------------------------- addresses
def local_addresses():
    """This computer's IPv4 addresses on local networks, the most likely Wi-Fi one first."""
    found = []
    try:
        from PySide6.QtNetwork import QNetworkInterface, QAbstractSocket
        for iface in QNetworkInterface.allInterfaces():
            flags = iface.flags()
            if not (flags & QNetworkInterface.IsUp and flags & QNetworkInterface.IsRunning) or \
                    flags & QNetworkInterface.IsLoopBack:
                continue
            for entry in iface.addressEntries():
                ip = entry.ip()
                if ip.protocol() == QAbstractSocket.IPv4Protocol:
                    found.append((ip.toString(), iface.humanReadableName() or iface.name()))
    except Exception:
        pass
    try:  # the address the system would use to reach the internet (no packet is sent)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        route_ip = s.getsockname()[0]
        s.close()
        if route_ip and not any(route_ip == a for a, _ in found):
            found.insert(0, (route_ip, ''))
    except OSError:
        route_ip = None

    def rank(item):
        ip, name = item
        n = (name or '').lower()
        private = ip.startswith('192.168.') or ip.startswith('10.') or \
            (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31)
        virtual = any(k in n for k in ('vmware', 'virtual', 'vbox', 'docker', 'hyper-v', 'vethernet', 'utun',
                                       'bridge', 'tailscale', 'zerotier', 'wsl'))
        wifi = any(k in n for k in ('wi-fi', 'wifi', 'wlan', 'wireless', 'en0', 'wlp'))
        return (ip.startswith('169.254.'), not private, virtual, ip != route_ip, not wifi)

    seen, ordered = set(), []
    for ip, name in sorted(found, key=rank):
        if ip not in seen and not ip.startswith('127.') and not ip.startswith('169.254.'):
            seen.add(ip)
            ordered.append((ip, name))
    return ordered


# --------------------------------------------------------------------- server

# --------------------------------------------------------------------- server
class PhoneServer:
    """A small upload server that lives only while the window is open.

    on_file(path)                     — a file arrived complete
    on_progress(id, name, done, total) — bytes received so far (for the window's progress)
    """

    def __init__(self, folder, on_file, language='en', computer=None, on_progress=None):
        self.folder = Path(folder)
        self.on_file = on_file
        self.on_progress = on_progress or (lambda *a: None)
        self.language = language
        self.computer = computer or socket.gethostname().split('.')[0]
        self.key = secrets.token_urlsafe(9)
        self.httpd = None
        self.thread = None
        self.port = None
        self.received = 0
        self.lock = threading.Lock()
        self.uploads = {}               # upload id → {'part', 'name', 'total', 'mtime'}

    def start(self):
        handler = self._handler()
        last = None
        for port in PORTS + [0]:
            try:
                self.httpd = ThreadingHTTPServer(('0.0.0.0', port), handler)
                break
            except OSError as exc:
                last = exc
        if self.httpd is None:
            raise OSError(f'Could not open a local port: {last}')
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, name='MorphixPhone', daemon=True)
        self.thread.start()
        return self.port

    def url(self, ip):
        return f'http://{ip}:{self.port}/{self.key}'

    def stop(self):
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
        with self.lock:
            for up in self.uploads.values():       # unfinished pieces are not kept
                try:
                    Path(up['part']).unlink()
                except OSError:
                    pass
            self.uploads.clear()

    # ------------------------------------------------------------ uploads
    def receive(self, upload_id, name, total, offset, length, mtime, stream):
        """Append one piece. Returns (http status, json dict)."""
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,64}', upload_id or ''):
            return 400, {'error': 'bad id'}
        if total <= 0 or total > MAX_FILE or length < 0 or offset < 0 or offset + length > total:
            return 413, {'error': 'bad size'}
        with self.lock:
            up = self.uploads.get(upload_id)
            if up is None:
                if offset != 0:
                    return 409, {'received': 0}
                self.folder.mkdir(parents=True, exist_ok=True)
                if shutil.disk_usage(self.folder).free < total + 300 * 1024 * 1024:
                    return 507, {'error': 'disk full'}
                part = self.folder / f'.{upload_id}.morphix-part'
                part.write_bytes(b'')
                up = {'part': str(part), 'name': safe_name(name), 'total': total, 'mtime': mtime, 'busy': False}
                self.uploads[upload_id] = up
            if up['busy']:
                return 409, {'received': Path(up['part']).stat().st_size}
            have = Path(up['part']).stat().st_size
            if have != offset:
                return 409, {'received': have}
            up['busy'] = True
        try:
            remaining = length
            with open(up['part'], 'ab') as f:
                while remaining > 0:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ConnectionError('The phone stopped sending.')
                    f.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            with self.lock:
                up['busy'] = False
                # drop a half-written piece so the phone can resend it cleanly
                with open(up['part'], 'r+b') as f:
                    f.truncate(offset)
            return 400, {'received': offset}
        done = offset + length
        self.on_progress(upload_id, up['name'], done, up['total'])
        if done < up['total']:
            with self.lock:
                up['busy'] = False
            return 200, {'received': done}
        with self.lock:
            dest = unique(self.folder, up['name'])
            os.replace(up['part'], dest)
            self.uploads.pop(upload_id, None)
        if up['mtime']:
            try:
                os.utime(dest, (time.time(), up['mtime']))   # keep the photo's / file's own date
            except OSError:
                pass
        self.received += 1
        try:
            self.on_file(str(dest))
        except Exception:
            pass
        return 200, {'received': done, 'done': True, 'name': dest.name}

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            server_version = 'Morphix'
            sys_version = ''

            def log_message(self, *args):
                pass

            def _send(self, code, body=b'', ctype='text/plain; charset=utf-8'):
                if isinstance(body, dict):
                    body, ctype = json.dumps(body).encode(), 'application/json'
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.end_headers()
                if body and self.command != 'HEAD':
                    self.wfile.write(body)

            def _route(self):
                path = self.path.split('?', 1)[0].rstrip('/')
                prefix = '/' + server.key
                if path == prefix:
                    return 'page'
                if path == prefix + '/upload':
                    return 'upload'
                return None

            def do_GET(self):
                if self._route() == 'page':
                    agent = self.headers.get('User-Agent', '')
                    self._send(200, page_html(server.language, server.computer, agent).encode('utf-8'),
                               'text/html; charset=utf-8')
                else:
                    self._send(404, b'Not found')

            do_HEAD = do_GET

            def do_POST(self):
                if self._route() != 'upload':
                    self.close_connection = True
                    self._send(404, b'Not found')
                    return

                def num(header, default=0):
                    try:
                        return int(float(self.headers.get(header, default)))
                    except (TypeError, ValueError):
                        return -1
                length = num('Content-Length')
                total = num('X-File-Size', length)
                offset = num('X-Offset')
                mtime = num('X-Last-Modified') / 1000.0
                upload_id = self.headers.get('X-Upload-Id') or secrets.token_hex(8)
                code, body = server.receive(upload_id, self.headers.get('X-File-Name', 'photo.jpg'), total,
                                            offset, length, mtime if mtime > 0 else 0, self.rfile)
                if code not in (200, 409):
                    self.close_connection = True   # an unread body must not be read as a new request
                elif code == 409:
                    # the piece was refused before reading: drain it so the connection stays usable
                    left = max(0, length)
                    while left > 0:
                        got = self.rfile.read(min(1024 * 1024, left))
                        if not got:
                            break
                        left -= len(got)
                self._send(code, body)

        return Handler


# --------------------------------------------------------------------- page
TEXT = {
    'en': {
        'title': 'Send to Morphix', 'to': 'To', 'camera': 'Take a photo', 'media': 'Photos & videos',
        'files': 'Files & documents', 'files_sub': 'PDF, Word, Excel, PowerPoint, ZIP, audio — any file',
        'media_sub': 'Original quality, any length',
        'tip': 'Take one photo per page. Hold the phone straight over the paper in good light.',
        'ios_title': 'Keep the original quality on iPhone',
        'ios': 'In the photo picker tap <b>Options</b> (iOS 17) or the <b>⚙︎ button at the bottom</b> (iOS 18+), '
               'then set <b>Format</b> to <b>Current</b>. Otherwise the iPhone turns photos into JPG and makes videos '
               'smaller before sending.',
        'sending': 'Sending…', 'sent': 'Sent', 'failed': 'Not sent — tap to try again', 'retry': 'Wi-Fi hiccup — retrying…',
        'done': 'They are on your computer now, in full quality. You can keep sending.',
        'lost': 'The computer stopped receiving. Open “From my phone” in Morphix again.',
        'full': 'Not enough space on the computer for this file.',
        'keep': 'Keep this page open until everything is sent.',
        'private': 'Only on your Wi-Fi · nothing goes to the internet',
    },
    'ar': {
        'title': 'أرسل إلى Morphix', 'to': 'إلى', 'camera': 'صوّر الآن', 'media': 'صور ومقاطع',
        'files': 'ملفات ومستندات', 'files_sub': 'PDF وWord وExcel وPowerPoint وZIP وصوتيات — أي ملف',
        'media_sub': 'بالجودة الأصلية، وبأي طول',
        'tip': 'صوّر كل صفحة في صورة. خلّ الجوال مستقيماً فوق الورقة وفي إضاءة جيدة.',
        'ios_title': 'للحفاظ على الجودة الأصلية في الآيفون',
        'ios': 'في نافذة اختيار الصور اضغط <b>Options</b> (iOS 17) أو <b>زر ⚙︎ في الأسفل</b> (iOS 18 وأحدث)، '
               'ثم اجعل <b>Format</b> على <b>Current</b>. غير كذا الآيفون يحوّل الصور إلى JPG ويصغّر المقاطع قبل الإرسال.',
        'sending': 'جارٍ الإرسال…', 'sent': 'تم الإرسال', 'failed': 'لم يُرسل — اضغط لإعادة المحاولة',
        'retry': 'انقطاع بسيط في الواي فاي — نعيد المحاولة…',
        'done': 'وصلت إلى جهازك بجودتها الكاملة. تقدر تكمل الإرسال.',
        'lost': 'الكمبيوتر توقف عن الاستقبال. افتح «من جوالي» في Morphix مرة ثانية.',
        'full': 'لا توجد مساحة كافية على الكمبيوتر لهذا الملف.',
        'keep': 'خلّ هذه الصفحة مفتوحة حتى ينتهي الإرسال.',
        'private': 'داخل شبكة الواي فاي فقط · لا شيء يذهب للإنترنت',
    },
}


def _logo_data():
    try:
        logo = Path(__file__).resolve().parent / 'assets' / 'morphix_logo.png'
        from PIL import Image
        import io
        with Image.open(logo) as im:
            im.thumbnail((128, 128))
            buf = io.BytesIO(); im.save(buf, 'PNG')
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ''


def page_html(language, computer, agent=''):
    t = TEXT['ar' if language == 'ar' else 'en']
    rtl = language == 'ar'
    esc = {k: (v if k == 'ios' else html.escape(v)) for k, v in t.items()}
    ios = bool(re.search(r'iPhone|iPad|iPod', agent or '')) or ('Macintosh' in (agent or '') and 'Mobile' in (agent or ''))
    msgs = json.dumps({k: t[k] for k in ('sending', 'sent', 'failed', 'retry', 'done', 'lost', 'full', 'keep')},
                      ensure_ascii=False)
    ios_card = f'''<div class="ios"><div class="ih">✨ {esc['ios_title']}</div><div>{esc['ios']}</div></div>''' if ios else ''
    return f'''<!doctype html><html lang="{'ar' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#06101E"><title>{esc['title']}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,"SF Arabic","Segoe UI",Tahoma,sans-serif;
background:#06101E;color:#EAF3FF;min-height:100vh;padding:22px 16px calc(28px + env(safe-area-inset-bottom))}}
header{{display:flex;align-items:center;gap:12px}}header img{{width:48px;height:48px;border-radius:12px}}
h1{{font-size:22px;margin:0}}.to{{color:#8FB6E8;font-size:14px;margin-top:2px}}
.btn{{display:flex;align-items:center;gap:14px;width:100%;border:0;border-radius:16px;padding:16px 18px;margin-top:12px;
color:#fff;background:#2F8CF5;cursor:pointer;text-align:start}}.btn.alt{{background:#132D52;border:1px solid #2C568A}}
.btn svg{{width:28px;height:28px;flex:none}}.btn b{{display:block;font-size:18px}}.btn small{{display:block;font-size:13px;opacity:.8;margin-top:2px}}
.ios{{margin-top:14px;background:#1B2E14;border:1px solid #3F6B2A;color:#D9F7C6;border-radius:14px;padding:12px 14px;font-size:14px;line-height:1.65}}
.ios .ih{{font-weight:700;margin-bottom:4px;color:#B8F28F}}.ios b{{color:#fff}}
.tip{{color:#9DB8DC;font-size:13px;line-height:1.6;margin:14px 2px 4px}}
.sum{{margin-top:14px;font-size:14px;color:#BFD6F5;display:none}}
.list{{margin-top:10px;display:grid;gap:10px}}
.item{{display:flex;align-items:center;gap:12px;background:#0E2240;border:1px solid #23466F;border-radius:14px;padding:10px}}
.item img,.item .ph{{width:54px;height:54px;border-radius:10px;object-fit:cover;background:#16345A;flex:none;
display:flex;align-items:center;justify-content:center;font-size:22px}}
.item .nm{{font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.item .st{{font-size:13px;color:#8FB6E8;margin-top:3px}}.item .st.ok{{color:#6EE7B7}}.item .st.err{{color:#FCA5A5}}
.meta{{flex:1;min-width:0}}.bar{{height:5px;background:#1B3A63;border-radius:4px;margin-top:6px;overflow:hidden}}
.bar i{{display:block;height:100%;width:0;background:#4FA3FF;transition:width .2s}}
.note{{margin-top:16px;color:#6EE7B7;font-size:14px;text-align:center;min-height:20px}}
footer{{margin-top:22px;text-align:center;color:#6F8DB5;font-size:12px}}
input{{display:none}}
</style></head><body>
<header><img src="{_logo_data()}" alt=""><div><h1>{esc['title']}</h1>
<div class="to">{esc['to']}: {html.escape(computer)}</div></div></header>
<label class="btn" for="cam"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg><span><b>{esc['camera']}</b><small>{esc['tip']}</small></span></label>
<input id="cam" type="file" accept="image/*" capture="environment">
<label class="btn alt" for="media"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 16l5-5 4 4 3-3 6 6"/></svg><span><b>{esc['media']}</b><small>{esc['media_sub']}</small></span></label>
<input id="media" type="file" accept="image/*,video/*" multiple>
<label class="btn alt" for="files"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/></svg><span><b>{esc['files']}</b><small>{esc['files_sub']}</small></span></label>
<input id="files" type="file" multiple>
{ios_card}
<div class="sum" id="sum"></div>
<div class="list" id="list"></div><div class="note" id="note"></div>
<footer>🔒 {esc['private']}</footer>
<script>
const M={msgs};const CHUNK={CHUNK};const BASE=location.pathname.replace(/\\/$/,'');
const list=document.getElementById('list'),note=document.getElementById('note'),sum=document.getElementById('sum');
let queue=[],active=0,lock=null,bytesSent=0,t0=0,pending=0;
function size(n){{const u=['B','KB','MB','GB'];let i=0;while(n>=1024&&i<3){{n/=1024;i++;}}return n.toFixed(i?1:0)+' '+u[i];}}
function uid(){{const a=new Uint8Array(12);crypto.getRandomValues(a);return Array.from(a,b=>('0'+b.toString(16)).slice(-2)).join('');}}
async function wake(on){{try{{if(on&&!lock&&navigator.wakeLock)lock=await navigator.wakeLock.request('screen');
  if(!on&&lock){{await lock.release();lock=null;}}}}catch(e){{}}}}
function row(file){{
  const r=document.createElement('div');r.className='item';let th;
  if(file.type.startsWith('image/')&&file.size<40e6){{th=document.createElement('img');th.src=URL.createObjectURL(file);}}
  else{{th=document.createElement('div');th.className='ph';th.textContent=file.type.startsWith('video/')?'🎬':file.type.startsWith('audio/')?'🎵':'📄';}}
  const m=document.createElement('div');m.className='meta';
  m.innerHTML='<div class="nm"></div><div class="st"></div><div class="bar"><i></i></div>';
  m.querySelector('.nm').textContent=(file.name||'photo.jpg')+'  ·  '+size(file.size);
  m.querySelector('.st').textContent=M.sending;r.append(th,m);list.prepend(r);return m;}}
function post(file,id,off,end){{return new Promise(res=>{{const x=new XMLHttpRequest();x.open('POST',BASE+'/upload');
  x.setRequestHeader('X-Upload-Id',id);x.setRequestHeader('X-File-Name',encodeURIComponent(file.name||('photo-'+Date.now()+'.jpg')));
  x.setRequestHeader('X-File-Size',String(file.size));x.setRequestHeader('X-Offset',String(off));
  x.setRequestHeader('X-Last-Modified',String(file.lastModified||0));
  x.upload.onprogress=e=>{{if(e.lengthComputable)x._p=e.loaded;}};x._p=0;
  x.onload=()=>{{let j={{}};try{{j=JSON.parse(x.responseText)}}catch(e){{}};res({{s:x.status,j}});}};
  x.onerror=()=>res({{s:0,j:{{}}}});x.ontimeout=()=>res({{s:0,j:{{}}}});x._file=file;
  x.send(file.slice(off,end));post.cur=x;}});}}
async function send(file,m){{
  const id=uid();let off=0,tries=0;const st=m.querySelector('.st'),bar=m.querySelector('i');
  if(file.size===0){{st.textContent=M.failed;st.className='st err';return;}}
  while(off<file.size){{const end=Math.min(off+CHUNK,file.size);const r=await post(file,id,off,end);
    if(r.s===200){{bytesSent+=end-off;off=r.j.received||end;tries=0;bar.style.width=(off*100/file.size)+'%';
      st.textContent=M.sending+' '+Math.floor(off*100/file.size)+'%';speed();continue;}}
    if(r.s===409&&typeof r.j.received==='number'){{off=r.j.received;continue;}}
    if(r.s===507){{st.textContent=M.full;st.className='st err';return;}}
    if(++tries>8){{st.textContent=M.failed;st.className='st err';note.textContent=M.lost;note.style.color='#FCA5A5';
      m.parentNode.onclick=()=>{{m.parentNode.onclick=null;st.className='st';enqueue(file,m);}};return;}}
    st.textContent=M.retry;await new Promise(z=>setTimeout(z,Math.min(8000,600*tries)));}}
  st.textContent='✓ '+M.sent+' · '+size(file.size);st.className='st ok';m.querySelector('.bar').style.display='none';
  note.style.color='#6EE7B7';note.textContent=M.done;}}
function speed(){{const s=(Date.now()-t0)/1000;if(s>1){{sum.style.display='block';
  sum.textContent='⇡ '+size(bytesSent/s)+'/s  ·  '+M.keep;}}}}
function enqueue(file,m){{queue.push([file,m]);pending++;pump();}}
function pump(){{while(active<2&&queue.length){{const [f,m]=queue.shift();active++;if(!t0)t0=Date.now();wake(true);
  send(f,m).finally(()=>{{active--;pending--;if(!pending){{wake(false);sum.style.display='none';t0=0;bytesSent=0;}}pump();}});}}}}
function take(input){{const files=[...input.files];input.value='';for(const f of files)enqueue(f,row(f));}}
for(const id of ['cam','media','files'])document.getElementById(id).onchange=e=>take(e.target);
window.addEventListener('beforeunload',e=>{{if(pending){{e.preventDefault();e.returnValue='';}}}});
</script></body></html>'''


# --------------------------------------------------------------------- window
def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024


def _short(name, limit=18):
    return name if len(name) <= limit else name[:8] + '…' + name[-8:]


def _dialog_classes():
    from PySide6.QtCore import QObject, Qt, QSize, QUrl, Signal, QTimer
    from PySide6.QtGui import QDesktopServices, QIcon, QImage, QPixmap
    from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
                                   QListWidgetItem, QPushButton, QVBoxLayout, QApplication)
    from i18n import tr, current

    class Bridge(QObject):
        arrived = Signal(str)
        progress = Signal(str, str, float, float)

    IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.heic', '.heif', '.tif', '.tiff')
    VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.3gp', '.webm')

    class PhoneDialog(QDialog):
        """QR code + live list of what the phone sends, with progress for big files."""

        def __init__(self, parent=None, purpose='files', folder=None):
            super().__init__(parent)
            from scan_dialog import STYLE
            self.setStyleSheet(STYLE + 'QLabel#url { color:#7FB9FF; font-size:13px; }'
                                       'QLabel#big { font-size:15px; font-weight:700; color:#FFFFFF; }'
                                       'QLabel#quality { color:#B8F28F; font-size:12px; }')
            self.setWindowTitle(tr('Morphix · From my phone'))
            self.purpose = purpose
            self.folder = Path(folder) if folder else default_folder()
            self.paths = []
            self.incoming = {}          # upload id → list item
            self._t0 = None
            self.bridge = Bridge()
            self.bridge.arrived.connect(self._arrived)
            self.bridge.progress.connect(self._progress)
            self.server = PhoneServer(self.folder, self.bridge.arrived.emit, language=current(),
                                      on_progress=lambda i, n, d, t: self.bridge.progress.emit(i, n, float(d), float(t)))
            self.resize(860, 580)

            root = QVBoxLayout(self); root.setContentsMargins(22, 18, 22, 16); root.setSpacing(10)
            title = QLabel(tr('Send photos, videos and files from your phone')); title.setObjectName('title')
            root.addWidget(title)
            hint = QLabel(tr('Your phone and this computer must be on the same Wi-Fi. Nothing goes through the '
                             'internet, and no app is needed on the phone.'))
            hint.setObjectName('hint'); hint.setWordWrap(True); root.addWidget(hint)

            body = QHBoxLayout(); body.setSpacing(16); root.addLayout(body, 1)
            card = QFrame(); card.setObjectName('card'); card.setFixedWidth(330)
            cl = QVBoxLayout(card); cl.setContentsMargins(16, 16, 16, 14); cl.setSpacing(8)
            self.qr = QLabel(); self.qr.setAlignment(Qt.AlignCenter); self.qr.setFixedSize(290, 290)
            cl.addWidget(self.qr, 0, Qt.AlignHCenter)
            steps = QLabel(tr('1. Open the camera on your phone and point it at the code.\n'
                              '2. Tap the link that appears.\n'
                              '3. Take photos or choose files — they arrive here.'))
            steps.setWordWrap(True); cl.addWidget(steps)
            self.url = QLabel(); self.url.setObjectName('url')
            self.url.setTextInteractionFlags(Qt.TextSelectableByMouse); self.url.setWordWrap(True)
            cl.addWidget(self.url)
            self.addr = QComboBox(); self.addr.currentIndexChanged.connect(self._show_qr)
            cl.addWidget(self.addr)
            body.addWidget(card)

            right = QVBoxLayout(); right.setSpacing(8)
            self.status = QLabel(tr('Waiting for your phone…')); self.status.setObjectName('big')
            right.addWidget(self.status)
            quality = QLabel('✦ ' + tr('Full quality: photos, videos and documents arrive exactly as the phone sends '
                                       'them — nothing is compressed here.'))
            quality.setObjectName('quality'); quality.setWordWrap(True); right.addWidget(quality)
            self.list = QListWidget(); self.list.setViewMode(QListWidget.IconMode)
            self.list.setIconSize(QSize(96, 96)); self.list.setResizeMode(QListWidget.Adjust)
            self.list.setGridSize(QSize(150, 178))
            self.list.setTextElideMode(Qt.ElideMiddle); self.list.setWordWrap(True)
            self.list.setMovement(QListWidget.Static)
            self.list.itemDoubleClicked.connect(self._open_item)
            right.addWidget(self.list, 1)
            where = QLabel(tr('Saved in: {folder}', folder=str(self.folder))); where.setObjectName('hint')
            where.setWordWrap(True); right.addWidget(where)
            fw = QLabel(tr('Phone can\'t open the page? Check both are on the same Wi-Fi (not a guest network), '
                           'and allow Morphix if your computer asks about incoming connections.'))
            fw.setObjectName('hint'); fw.setWordWrap(True); right.addWidget(fw)
            body.addLayout(right, 1)

            foot = QHBoxLayout()
            self.open_btn = QPushButton(tr('Open the folder')); self.open_btn.clicked.connect(self._open_folder)
            foot.addWidget(self.open_btn); foot.addStretch()
            close = QPushButton(tr('Close')); close.clicked.connect(self.reject)
            foot.addWidget(close)
            label = tr('Scan these photos') if purpose == 'scan' else tr('Use these files')
            self.use = QPushButton(label); self.use.setObjectName('primary'); self.use.setEnabled(False)
            self.use.clicked.connect(self.accept)
            foot.addWidget(self.use)
            root.addLayout(foot)

            try:
                self.server.start()
            except OSError as exc:
                self.status.setText(tr('Could not start receiving: {error}', error=str(exc)))
                return
            addresses = local_addresses()
            for ip, name in addresses:
                self.addr.addItem(f'{ip}' + (f'  ·  {name}' if name else ''), ip)
            self.addr.setVisible(len(addresses) > 1)
            if not addresses:
                self.status.setText(tr('This computer is not connected to a network. Connect it to Wi-Fi first.'))
            self._show_qr()

        def _show_qr(self):
            ip = self.addr.currentData()
            if not ip or not self.server.port:
                self.qr.clear()
                return
            url = self.server.url(ip)
            self.url.setText(url)
            import qr_maker
            img = qr_maker.render(url, style='rounded', fg='#0B1A2E', size=580, border=3)
            data = img.convert('RGBA').tobytes()
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888).copy()
            self.qr.setPixmap(QPixmap.fromImage(qimg).scaled(290, 290, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        def _progress(self, upload_id, name, done, total):
            item = self.incoming.get(upload_id)
            if item is None:
                item = QListWidgetItem(name)
                item.setIcon(self._kind_icon(name))
                self.list.insertItem(0, item)
                self.incoming[upload_id] = item
                if self._t0 is None:
                    self._t0 = time.monotonic()
            item.setText(f'{_short(name)}\n{int(done * 100 / max(total, 1))}%  ·  {human_size(total)}')
            self.status.setText(tr('Receiving… {n} received so far', n=len(self.paths)))
            if done >= total:            # the finished file replaces its progress tile
                self.incoming.pop(upload_id, None)
                row = self.list.row(item)
                if row >= 0:
                    self.list.takeItem(row)

        def _kind_icon(self, name):
            from PySide6.QtGui import QPainter, QColor, QFont
            pix = QPixmap(96, 96); pix.fill(Qt.transparent)
            p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor('#16345A')); p.setPen(Qt.NoPen); p.drawRoundedRect(4, 4, 88, 88, 14, 14)
            ext = Path(name).suffix.lower()
            label = 'VIDEO' if ext in VIDEO_EXT else (ext[1:5].upper() or 'FILE')
            f = QFont(); f.setPixelSize(17); f.setBold(True); p.setFont(f); p.setPen(QColor('#9CC8F5'))
            p.drawText(pix.rect(), Qt.AlignCenter, label)
            p.end()
            return QIcon(pix)

        def _thumb(self, path):
            ext = Path(path).suffix.lower()
            if ext in IMAGE_EXT:
                try:
                    from PIL import Image, ImageOps
                    try:
                        import tools_engine
                        tools_engine.register_heic()
                    except Exception:
                        pass
                    with Image.open(path) as im:
                        im = ImageOps.exif_transpose(im)
                        im.thumbnail((192, 192))
                        im = im.convert('RGBA')
                        q = QImage(im.tobytes(), im.width, im.height, QImage.Format_RGBA8888).copy()
                        return QIcon(QPixmap.fromImage(q))
                except Exception:
                    pass
            if ext in VIDEO_EXT:
                try:
                    from action_dialogs import _frame_pixmap
                    pix = _frame_pixmap(path, 0.5, width=192)
                    if pix is not None:
                        return QIcon(pix)
                except Exception:
                    pass
            return self._kind_icon(Path(path).name)

        def _arrived(self, path):
            self.paths.append(path)
            name = Path(path).name
            size = human_size(Path(path).stat().st_size) if Path(path).exists() else ''
            item = QListWidgetItem(f'{_short(name)}\n{size}')
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            item.setIcon(self._thumb(path))
            self.list.insertItem(0, item)
            self.status.setText(tr('{n} received', n=len(self.paths)))
            self.use.setEnabled(True)
            QApplication.alert(self)

        def _open_item(self, item):
            path = item.data(Qt.UserRole)
            if path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

        def _open_folder(self):
            self.folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder)))

        def received_paths(self):
            return [p for p in self.paths if Path(p).is_file()]

        def done(self, result):
            self.server.stop()
            super().done(result)

    return PhoneDialog


def __getattr__(name):
    if name == 'PhoneDialog':
        cls = _dialog_classes()
        globals()['PhoneDialog'] = cls
        return cls
    raise AttributeError(name)
