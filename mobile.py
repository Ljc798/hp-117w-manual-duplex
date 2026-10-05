#!/usr/bin/env python3
"""Local-only controls for the macOS manual duplex workflow (standard library)."""
import contextlib
import datetime as dt
import fcntl
import http.server
import json
import os
import re
import secrets
import shutil
import socketserver
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

STATE = Path.home() / 'Library/Application Support/HP117wMobile'
RESOURCES = Path(__file__).resolve().parent
PORT = 8717
MAX_UPLOAD = 50 * 1024 * 1024
APP = Path.home() / 'Applications/HP 117w Manual Duplex.app'


def initialize():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    (STATE / 'jobs').mkdir(exist_ok=True, mode=0o700)


@contextlib.contextmanager
def locked():
    initialize()
    with (STATE / 'state.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def write(name, value):
    target = STATE / name
    tmp = target.with_name(target.name + '.' + secrets.token_hex(6) + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False))
    os.replace(tmp, target)


def read(name, default=None):
    try:
        return json.loads((STATE / name).read_text())
    except (FileNotFoundError, ValueError):
        return default


def command(args, timeout=30):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()


def pdf_command(*args):
    return command(['/usr/bin/osascript', '-l', 'JavaScript', str(RESOURCES / 'duplex.js'), *map(str, args)])


@contextlib.contextmanager
def db():
    conn = sqlite3.connect(STATE / 'history.sqlite3', timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute('CREATE TABLE IF NOT EXISTS records\n                (id TEXT PRIMARY KEY, printed_at TEXT, name TEXT, pages INTEGER,\n                 sheets INTEGER, printer TEXT, status TEXT, note TEXT)')
            yield conn
    finally:
        conn.close()


def import_excel_history():
    """One-time read-only import of the existing Excel log; no Excel dependency."""
    if (STATE / 'excel-imported').exists():
        return
    path = Path.home() / 'Documents/HP 117w Manual Duplex Print Log.xlsx'
    if not path.exists():
        return
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.findall('s:sheets/s:sheet', ns)
        chosen = next((s for s in sheets if s.get('name') == 'Print Log'), sheets[0])
        rid = chosen.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        target = next(r.get('Target') for r in rels if r.get('Id') == rid)
        sheet = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        rows = ET.fromstring(archive.read(sheet)).findall('s:sheetData/s:row', ns)
        epoch = dt.datetime(1904, 1, 1) if workbook.find('s:workbookPr', ns) is not None and workbook.find('s:workbookPr', ns).get('date1904') == '1' else dt.datetime(1899, 12, 30)
        with db() as conn:
            for index, row in enumerate(rows[1:]):
                cells = {}
                for cell in row.findall('s:c', ns):
                    col = re.sub('[0-9]', '', cell.get('r', ''))
                    value = cell.findtext('s:v', default='', namespaces=ns)
                    if cell.get('t') == 's':
                        value = shared[int(value)]
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(cell.find('s:is', ns).itertext())
                    cells[col] = value
                if not cells.get('B'):
                    continue
                timestamp = cells.get('A', '')
                try:
                    timestamp = (epoch + dt.timedelta(days=float(timestamp))).isoformat(timespec='seconds')
                except ValueError:
                    pass
                conn.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?,?,?,?,?)', (
                    'legacy-' + str(index), timestamp, cells['B'], int(float(cells.get('C') or 0)),
                    int(float(cells.get('D') or 0)), cells.get('E', ''), cells.get('F', ''), cells.get('G', '')))
    (STATE / 'excel-imported').touch()


def active_job():
    job = read('active.json', {})
    if job.get('pending') and time.time() - job.get('reserved_at', 0) > 90:
        write('active.json', {})
        write('prompt.json', {'id': secrets.token_hex(16), 'key': 'launch_error', 'message': '', 'stage': 'error', 'buttons': []})
        return {}
    return job


def state():
    with locked():
        job = active_job()
        prompt = read('prompt.json', {'id': 'idle', 'key': 'idle', 'message': '', 'buttons': [], 'stage': 'ready'})
        prompt['job'] = {k: job[k] for k in ('id', 'name', 'pages', 'sheets', 'printer', 'mode') if k in job}
        prompt['active'] = bool(job)
        prompt['version'] = 2
        return prompt


def publish(message='', buttons=(), key='notice', stage='ready', note=False):
    ident = secrets.token_hex(16)
    with locked():
        write('prompt.json', {'id': ident, 'message': message, 'key': key, 'stage': stage, 'buttons': list(buttons), 'note': note})
    return ident


def answer(data):
    with locked():
        prompt = read('prompt.json', {})
        if data.get('id') != prompt.get('id') or data.get('button') not in prompt.get('buttons', []):
            return False
        write('prompt.json', {**prompt, 'id': secrets.token_hex(16), 'key': 'processing', 'message': '', 'buttons': []})
        write('answer.json', data)
    return True


def wait_answer(ident):
    while True:
        with locked():
            reply = read('answer.json', {})
        if reply.get('id') == ident:
            return reply
        time.sleep(.25)


def ask(message, note, buttons):
    if 'Print First Side' in buttons:
        key, stage = 'review', 'ready'
    elif 'Continue' in buttons:
        key, stage = 'reload', 'reload'
    elif note:
        key, stage = 'note', 'note'
    elif 'Not Now' in buttons:
        key, stage = 'complete', 'done'
    elif 'Confirm Printed' in buttons:
        key, stage = 'confirm', 'confirm'
    else:
        key, stage = 'notice', 'error'
    return wait_answer(publish(message, buttons, key, stage, note))


def wait_queue(queue, stage):
    with locked():
        job = active_job()
    if stage == 'back_wait' and (job.get('mode') == 'single' or job.get('pages') == 1):
        stage = 'front_wait'
    ident = publish('', ['Cancel'], 'waiting', stage)
    while True:
        with locked():
            reply = read('answer.json', {})
        if reply.get('id') == ident:
            return 'Cancel'
        try:
            pending = command(['/usr/bin/lpstat', '-W', 'not-completed', '-o', queue], timeout=10)
        except (subprocess.SubprocessError, OSError) as error:
            result = wait_answer(publish(str(error), ['Retry', 'Cancel'], 'queue_error', stage))
            if result['button'] == 'Cancel':
                return 'Cancel'
            ident = publish('', ['Cancel'], 'waiting', stage)
            continue
        if not pending:
            # Recheck cancellation under the same lock before advancing.
            with locked():
                if read('answer.json', {}).get('id') == ident:
                    return 'Cancel'
            return 'Ready'
        time.sleep(2)


def new_job(source, name, queue='', printer='', mode='duplex', ident=None):
    ident = ident or secrets.token_hex(16)
    directory = STATE / 'jobs' / ident
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / 'source.pdf'
    if Path(source).resolve() != target.resolve():
        shutil.copyfile(source, target)
    count = int(pdf_command('--count', target))
    job = {'id': ident, 'source': str(target), 'name': name, 'pages': count,
           'sheets': count if mode == 'single' else (count + 1) // 2, 'mode': mode,
           'queue': queue, 'printer': printer, 'started_at': dt.datetime.now().astimezone().isoformat(timespec='seconds')}
    write('jobs/' + ident + '/job.json', job)
    return job


def begin(source, queue, printer):
    with locked():
        current = active_job()
        if current and (not current.get('pending') or Path(current['source']).resolve() != Path(source).resolve()):
            raise RuntimeError('A print session is already active. Finish it on the control page first.')
        if current:
            current.update(pending=False, queue=queue, printer=printer)
            job = current
        else:
            job = new_job(source, Path(source).name.removesuffix('.pdf.pdf') + ('.pdf' if Path(source).name.endswith('.pdf.pdf') else ''), queue, printer)
        write('active.json', job)
        write('jobs/' + job['id'] + '/job.json', job)
        return job['mode']


def record(name, pages, sheets, status, note):
    with locked():
        job = active_job()
        ident = job.get('id', secrets.token_hex(16))
        with db() as conn:
            conn.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?)', (
                ident, dt.datetime.now().astimezone().isoformat(timespec='seconds'), job.get('name', name),
                int(pages), int(sheets), job.get('printer', ''), status, note))


def history():
    with locked():
        try:
            import_excel_history()
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, IndexError, StopIteration):
            pass
        with db() as conn:
            result = [dict(row) for row in conn.execute('SELECT * FROM records ORDER BY printed_at DESC LIMIT 200')]
        for item in result:
            item['can_reprint'] = (STATE / 'jobs' / item['id'] / 'source.pdf').is_file()
        return result


def open_app(source):
    subprocess.run(['/usr/bin/open', '-a', str(APP), source], check=True, timeout=15)


def launch_job(job):
    write('active.json', {**job, 'pending': True, 'reserved_at': time.time()})
    write('prompt.json', {'id': secrets.token_hex(16), 'key': 'preparing', 'message': '', 'stage': 'ready', 'buttons': []})
    try:
        open_app(job['source'])
    except (OSError, subprocess.SubprocessError):
        write('active.json', {})
        write('prompt.json', {'id': secrets.token_hex(16), 'key': 'launch_error', 'message': '', 'stage': 'error', 'buttons': []})
        raise


def upload_pdf(data, name):
    if not data or len(data) > MAX_UPLOAD or b'%PDF-' not in data[:1024]:
        raise ValueError('invalid_pdf')
    # Names are display-only; files live under a generated private job ID.
    name = Path(name.replace('\\', '/')).name[:160]
    name = ''.join(c for c in name if ord(c) >= 32) or 'Uploaded.pdf'
    with locked():
        if active_job():
            raise ValueError('busy')
        ident = secrets.token_hex(16)
        directory = STATE / 'jobs' / ident
        directory.mkdir(mode=0o700)
        source = directory / 'source.pdf'
        source.write_bytes(data)
        job = new_job(source, name, ident=ident)
        launch_job(job)
        return job['id']


def reprint(data):
    ident = data.get('record_id', '')
    if not re.fullmatch('[a-f0-9]{32}', ident):
        raise ValueError('source_missing')
    mode = data.get('mode', 'duplex')
    if mode not in ('duplex', 'single'):
        raise ValueError('invalid_range')
    with locked():
        if active_job():
            raise ValueError('busy')
        source = STATE / 'jobs' / ident / 'source.pdf'
        with db() as conn:
            row = conn.execute('SELECT * FROM records WHERE id=?', (ident,)).fetchone()
        if row is None or not source.is_file():
            raise ValueError('source_missing')
        first, last = data.get('first'), data.get('last')
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= row['pages']:
            raise ValueError('invalid_range')
        new_id = secrets.token_hex(16)
        directory = STATE / 'jobs' / new_id
        directory.mkdir(mode=0o700)
        extracted = directory / 'source.pdf'
        pdf_command('--extract', source, extracted, first, last)
        job = new_job(extracted, row['name'] + ' (pages %s–%s)' % (first, last), mode=mode, ident=new_id)
        launch_job(job)
        return job['id']


def serve(token):
    class Server(http.server.ThreadingHTTPServer):
        def server_bind(self):
            socketserver.TCPServer.server_bind(self)
            self.server_name = 'HP117w'
            self.server_port = self.server_address[1]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def respond(self, status, data, kind='application/json'):
            if not isinstance(data, (str, bytes)):
                data = json.dumps(data, ensure_ascii=False)
            if isinstance(data, str):
                data = data.encode()
            self.send_response(status)
            self.send_header('Content-Type', kind + ('; charset=utf-8' if kind != 'image/png' else ''))
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            prefix = '/' + token + '/'
            if not path.startswith(prefix):
                return self.respond(404, {})
            endpoint = path[len(prefix):]
            if not endpoint:
                return self.respond(200, (RESOURCES / 'mobile.html').read_text(), 'text/html')
            if endpoint == 'qr.png' and (STATE / 'qr.png').exists():
                return self.respond(200, (STATE / 'qr.png').read_bytes(), 'image/png')
            if endpoint == 'state':
                return self.respond(200, state())
            if endpoint == 'history':
                return self.respond(200, history())
            return self.respond(404, {})
        def do_POST(self):
            prefix = '/' + token + '/'
            if not self.path.startswith(prefix):
                return self.respond(404, {})
            endpoint = self.path[len(prefix):]
            if endpoint not in ('answer', 'upload', 'reprint'):
                return self.respond(404, {})
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self.respond(403, {'error': 'origin'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                limit = MAX_UPLOAD if endpoint == 'upload' else 20000
                if not 0 < size <= limit:
                    return self.respond(413, {'error': 'too_large'})
                self.connection.settimeout(30)
                body = self.rfile.read(size)
                if len(body) != size:
                    raise ValueError('invalid_request')
                if endpoint == 'upload':
                    if self.headers.get_content_type() != 'application/pdf':
                        raise ValueError('invalid_pdf')
                    name = urllib.parse.unquote(self.headers.get('X-Filename', 'Uploaded.pdf'))
                    return self.respond(202, {'id': upload_pdf(body, name)})
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ValueError('invalid_request')
                if endpoint == 'reprint':
                    return self.respond(202, {'id': reprint(data)})
                if not isinstance(data.get('note', ''), str) or len(data.get('note', '')) > 4000:
                    raise ValueError('invalid_request')
                if not answer(data):
                    return self.respond(409, {'error': 'stale'})
                return self.respond(200, {})
            except ValueError as error:
                reason = str(error)
                return self.respond(409 if reason == 'busy' else 400, {'error': reason})
            except (OSError, subprocess.SubprocessError):
                return self.respond(500, {'error': 'operation_failed'})
    servers = [Server(('127.0.0.1', PORT), Handler)]
    for server in servers:
        server.daemon_threads = True
    if not os.environ.get('HP117W_TEST'):
        for interface in ('en0', 'en1'):
            address = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', interface], capture_output=True, text=True).stdout.strip()
            if address and address not in [s.server_address[0] for s in servers]:
                servers.append(Server((address, PORT), Handler))
    write('server.json', {'pid': os.getpid()})
    for server in servers[1:]:
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
    servers[0].serve_forever()


def start(token):
    def ready():
        try:
            url = 'http://127.0.0.1:%d/%s/state' % (PORT, token)
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=1) as response:
                return response.status == 200 and json.load(response).get('version') == 2
        except Exception:
            return False
    if not ready():
        with (STATE / 'server.log').open('a') as log:
            subprocess.Popen([sys.executable, __file__, 'serve'], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        for _ in range(50):
            if ready():
                break
            time.sleep(.1)
        else:
            raise RuntimeError('The mobile control service could not start. Restart the old service or check port 8717.')
    host = command(['/usr/sbin/scutil', '--get', 'LocalHostName']) + '.local'
    url = 'http://%s:%d/%s/' % (host, PORT, token)
    # CoreImage QR encoding must be ASCII, including the existing fixed token.
    pdf_command('--qr', url, STATE / 'qr.png')
    return url


def main():
    initialize()
    with locked():
        if not (STATE / 'token').exists():
            (STATE / 'token').write_text(secrets.token_urlsafe(24))
            os.chmod(STATE / 'token', 0o600)
        token = (STATE / 'token').read_text()
    cmd, *args = sys.argv[1:]
    if cmd == 'serve':
        serve(token)
    elif cmd == 'start':
        print(start(token))
    elif cmd == 'begin':
        print(begin(*args))
    elif cmd == 'source':
        with locked():
            print(active_job()['source'])
    elif cmd == 'name':
        with locked():
            print(active_job().get('name', 'PDF'))
    elif cmd == 'ask':
        result = ask(args[0], args[1] == 'note', args[2:])
        print(result['button'] + '\n' + result.get('note', ''))
    elif cmd == 'wait':
        print(wait_queue(*args))
    elif cmd == 'record':
        record(*args)
    elif cmd == 'finish':
        with locked():
            write('active.json', {})
            write('prompt.json', {'id': secrets.token_hex(16), 'key': 'idle', 'stage': 'ready', 'message': '', 'buttons': []})
    else:
        raise ValueError('Unknown mobile helper command')

if __name__ == '__main__':
    main()
