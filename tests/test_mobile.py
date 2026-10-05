import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mobile', ROOT / 'mobile.py')
mobile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mobile)


def sample_pdf(path, count=7):
    """Small valid PDF with numbered pages for real PDFKit ordering checks."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               ('<< /Type /Pages /Count %d /Kids [%s] >>' % (count, ' '.join('%d 0 R' % (4 + i * 2) for i in range(count)))).encode(),
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for i in range(count):
        objects.append(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>' % (5 + i * 2)).encode())
        content = ('BT /F1 24 Tf 50 700 Td (Page %d) Tj ET' % (i + 1)).encode()
        objects.append(b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += ('%d 0 obj\n' % i).encode() + obj + b'\nendobj\n'
    xref = len(data)
    data += ('xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)).encode()
    for offset in offsets[1:]: data += ('%010d 00000 n \n' % offset).encode()
    data += ('trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref)).encode()
    path.write_bytes(data)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = mobile.STATE
        mobile.STATE = Path(self.directory.name)
        mobile.initialize()
        self.pdf = mobile.STATE / 'test.pdf'
        sample_pdf(self.pdf)
        self.pdf_mock = patch.object(mobile, 'pdf_command', return_value='7')
        self.pdf_mock.start()
    def tearDown(self):
        self.pdf_mock.stop()
        mobile.STATE = self.previous
        self.directory.cleanup()
    def test_begin_is_exclusive_and_archives_source(self):
        self.assertEqual(mobile.begin(self.pdf, 'queue', 'Printer'), 'duplex')
        job = mobile.active_job()
        self.assertEqual(Path(job['source']).read_bytes(), self.pdf.read_bytes())
        with self.assertRaises(RuntimeError): mobile.begin(self.pdf, 'queue', 'Printer')
    def test_duplicate_answers_and_old_step_are_rejected(self):
        ident = mobile.publish('Reload', ['Continue'], 'reload', 'reload')
        payload = {'id': ident, 'button': 'Continue', 'note': '中文\nEnglish'}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(lambda _: mobile.answer(payload), range(2)))
        self.assertEqual(sorted(outcomes), [False, True])
        mobile.publish('Note', ['Save Record'], 'note', 'note', True)
        self.assertFalse(mobile.answer(payload))
        self.assertEqual(mobile.read('answer.json')['note'], '中文\nEnglish')
    def test_busy_upload_never_launches(self):
        mobile.begin(self.pdf, 'queue', 'Printer')
        with patch.object(mobile, 'open_app') as launch:
            with self.assertRaisesRegex(ValueError, 'busy'):
                mobile.upload_pdf(self.pdf.read_bytes(), 'test.pdf')
            launch.assert_not_called()
    def test_pending_upload_is_claimed_and_name_preserved(self):
        with patch.object(mobile, 'open_app') as launch:
            ident = mobile.upload_pdf(self.pdf.read_bytes(), '../My Notes.pdf')
            self.assertEqual(launch.call_count, 1)
        job = mobile.active_job()
        self.assertEqual(job['name'], 'My Notes.pdf')
        self.assertEqual(mobile.begin(job['source'], 'queue', 'Printer'), 'duplex')
        self.assertEqual(mobile.active_job()['id'], ident)
        self.assertFalse(mobile.active_job()['pending'])
    def test_history_record_preserves_partial_status(self):
        mobile.begin(self.pdf, 'queue', 'Printer')
        mobile.record('test.pdf', 7, 4, 'Partial: first side only', 'Notes')
        record = mobile.history()[0]
        self.assertTrue(record['can_reprint'])
        self.assertEqual(record['status'], 'Partial: first side only')
    def test_invalid_reprint_range_and_traversal_never_launch(self):
        mobile.begin(self.pdf, 'queue', 'Printer')
        mobile.record('test.pdf', 7, 4, 'Printed', '')
        ident = mobile.active_job()['id']
        mobile.write('active.json', {})
        with patch.object(mobile, 'open_app') as launch:
            for first, last in [(0, 7), (1, 8), (4, 3), (True, 7)]:
                with self.assertRaisesRegex(ValueError, 'invalid_range'):
                    mobile.reprint({'record_id': ident, 'first': first, 'last': last})
            with self.assertRaisesRegex(ValueError, 'source_missing'):
                mobile.reprint({'record_id': '../source', 'first': 1, 'last': 2})
            launch.assert_not_called()
    def test_queue_monitor_exits_without_user_check_click(self):
        with patch.object(mobile, 'command', side_effect=['queue-1 user 512', '']), patch.object(mobile.time, 'sleep'):
            self.assertEqual(mobile.wait_queue('queue', 'front_wait'), 'Ready')
    def test_queue_monitor_cancel_stops_progress(self):
        def pending(*args, **kwargs):
            mobile.answer({'id': mobile.state()['id'], 'button': 'Cancel'})
            return ''
        with patch.object(mobile, 'command', side_effect=pending):
            self.assertEqual(mobile.wait_queue('queue', 'back_wait'), 'Cancel')

    def test_draft_uploads_queue_without_starting_app(self):
        with patch.object(mobile, 'open_app') as launch:
            a = mobile.upload_pdf(self.pdf.read_bytes(), 'A.pdf', draft=True)
            b = mobile.upload_pdf(self.pdf.read_bytes(), 'B.pdf', draft=True)
            launch.assert_not_called()
            self.assertFalse(mobile.active_job())
            self.assertEqual([j['id'] for j in mobile.library()['queue']], [a, b])
            mobile.start_draft({'id': a})
            self.assertEqual(launch.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'busy'):
                mobile.start_draft({'id': b})

    def test_queued_pdf_cannot_be_trashed(self):
        ident = mobile.upload_pdf(self.pdf.read_bytes(), 'queued.pdf', draft=True)
        with self.assertRaisesRegex(ValueError, 'busy'):
            mobile.discard_cache({'id': ident})
        self.assertTrue(Path(mobile.get_job(ident)['source']).exists())

    def test_interrupted_session_recovery_requires_dead_owner_and_empty_queue(self):
        mobile.begin(self.pdf, 'queue', 'Printer')
        job=mobile.active_job();job.update(owner_pid=999999,phase='reload');mobile.write('active.json',job)
        with patch.object(mobile, 'owner_alive', return_value=False):
            self.assertEqual(mobile.state()['key'],'recovery')
            with patch.object(mobile, 'command', return_value='queue-1 pending'):
                with self.assertRaisesRegex(ValueError,'printer_busy'):
                    mobile.recover({'action':'restart'})
            with patch.object(mobile, 'command', return_value=''):
                mobile.recover({'action':'restart'})
            self.assertFalse(mobile.active_job())
        self.assertEqual(len(mobile.library()['queue']),1)
        self.assertEqual(mobile.history()[0]['status'],'Interrupted; completion unconfirmed')

    def test_search_and_partial_filter(self):
        mobile.begin(self.pdf,'queue','Printer')
        mobile.record('test.pdf',7,4,'Partial: first side only','Find this note')
        self.assertEqual(len(mobile.history('Find this note','partial')),1)
        self.assertEqual(mobile.history('Find this note','printed'),[])

    def test_cache_moves_to_trash_and_keeps_history(self):
        mobile.begin(self.pdf,'queue','Printer')
        job=mobile.active_job();mobile.record('test.pdf',7,4,'Printed','')
        mobile.write('active.json',{})
        with patch.object(mobile.Path,'home',return_value=mobile.STATE/'fake-home'):
            mobile.discard_cache({'id':job['id']})
        self.assertFalse(Path(job['source']).exists())
        self.assertTrue(list((mobile.STATE/'fake-home/.Trash').rglob('source.pdf')))
        self.assertEqual(mobile.history()[0]['status'],'Printed')
        self.assertFalse(mobile.history()[0]['can_reprint'])


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.previous_state, cls.previous_port = mobile.STATE, mobile.PORT
        mobile.STATE, mobile.PORT = Path(cls.directory.name), 18719
        mobile.initialize()
        os.environ['HP117W_TEST'] = '1'
        cls.thread = threading.Thread(target=mobile.serve, args=('test-token',), daemon=True)
        cls.thread.start()
        time.sleep(.15)
        cls.base = 'http://127.0.0.1:18719/test-token/'
    @classmethod
    def tearDownClass(cls):
        # Daemon server terminates with the test process; no live printer endpoint is touched.
        mobile.STATE, mobile.PORT = cls.previous_state, cls.previous_port
        cls.directory.cleanup()
    def request(self, endpoint, body=None, headers=None):
        request = urllib.request.Request(self.base + endpoint, data=body, headers=headers or {})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=3) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
    def test_page_and_bilingual_assets(self):
        code, page = self.request('')
        self.assertEqual(code, 200)
        self.assertIn('中文'.encode(), page)
        self.assertIn(b'localStorage', page)
        self.assertEqual(json.loads(self.request('state')[1])['version'], 3)
    def test_wrong_token_and_cross_origin_rejected(self):
        self.assertEqual(self.request('../wrong/state')[0], 404)
        payload = json.dumps({'id': 'x', 'button': 'Continue'}).encode()
        self.assertEqual(self.request('answer', payload, {'Origin': 'http://untrusted.invalid'})[0], 403)
    def test_invalid_request_and_pdf_rejected(self):
        self.assertEqual(self.request('answer', b'[]')[0], 400)
        self.assertEqual(self.request('upload', b'Not a PDF', {'Content-Type': 'application/pdf'})[0], 400)


class PDFKitTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('HP117W_PDFKIT_TEST'), 'Enable for real macOS PDFKit validation')
    def test_extract_and_duplex_order(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / 'source.pdf'; sample_pdf(source)
            extracted = directory / 'range.pdf'
            self.assertEqual(mobile.pdf_command('--extract', source, extracted, 2, 5), '4')
            mobile.pdf_command('--prepare', source, directory, 1, 7)
            inspector = directory / 'inspect.js'
            inspector.write_text("ObjC.import('Foundation');ObjC.import('Quartz');function run(args){var d=$.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(args[0]));var out=[];for(var i=0;i<Number(d.pageCount);i++){var p=d.pageAtIndex(i);out.push({text:ObjC.unwrap(p.string).trim(),rotation:Number(p.rotation)});}return JSON.stringify(out);}")
            def inspect(path):
                return json.loads(mobile.command(['/usr/bin/osascript', '-l', 'JavaScript', str(inspector), str(path)]))
            self.assertEqual([p['text'] for p in inspect(extracted)], ['Page 2', 'Page 3', 'Page 4', 'Page 5'])
            self.assertEqual([p['text'] for p in inspect(directory / 'odd.pdf')], ['Page 1', 'Page 3', 'Page 5', 'Page 7'])
            even = inspect(directory / 'even.pdf')
            self.assertEqual([p['text'] for p in even], ['Page 6', 'Page 4', 'Page 2'])
            self.assertTrue(all(p['rotation'] == 180 for p in even))
            previous = mobile.STATE
            try:
                mobile.STATE = directory / 'state'; mobile.initialize()
                mobile.begin(source, 'test-queue', 'Test printer')
                mobile.record('source.pdf', 7, 4, 'Partial: first side only', '')
                ident = mobile.active_job()['id']; mobile.write('active.json', {})
                with patch.object(mobile, 'open_app') as launch:
                    new_id = mobile.reprint({'record_id': ident, 'first': 3, 'last': 4, 'mode': 'single'})
                    self.assertEqual(launch.call_count, 1)
                job = mobile.active_job()
                self.assertEqual((job['id'], job['mode'], job['pages'], job['sheets']), (new_id, 'single', 2, 2))
                self.assertEqual([p['text'] for p in inspect(Path(job['source']))], ['Page 3', 'Page 4'])
                self.assertEqual(mobile.begin(job['source'], 'queue', 'Printer'), 'single')
                mobile.apply_settings(mobile.active_job(), {'first':1,'last':2,'copies':3,'mode':'duplex'})
                self.assertEqual(len(mobile.read('queue.json')),2)
                self.assertEqual(mobile.active_job()['copy_total'],3)
                for ident in mobile.read('queue.json'):
                    self.assertEqual(mobile.get_job(ident)['pages'],2)
                preview,kind=mobile.preview_file('preview/'+job['id']+'/1.png')
                self.assertEqual(kind,'image/png')
                self.assertTrue(preview.startswith(b'\x89PNG\r\n\x1a\n'))
            finally:
                mobile.STATE = previous

if __name__ == '__main__': unittest.main()
