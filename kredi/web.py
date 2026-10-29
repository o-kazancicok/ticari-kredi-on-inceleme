import json
import re
import threading
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler
from .config import ROOT, DATA_DIR, MODE, AS_OF, DISCLAIMER
from . import storage, service
from .seed import seed, document
from .documents import ingest
from .policy import POLICY
from .operations import critical, reset_session, close_session, snapshot, SessionLogHandler, discard_legacy_logs

LOCK = threading.RLock()
LOGGER = logging.getLogger('kredi.web')


class Handler(BaseHTTPRequestHandler):
    server_version = 'KrediDosyasi/1.0'

    def log_message(self, format, *args):
        # Routine access logs do not add useful operation history.
        pass

    def log_request(self, code='-', size='-'):
        if str(code).isdigit() and int(code) >= 400:
            LOGGER.warning('HTTP isteği başarısız (status=%s)', code)

    def send(self, code, payload, content_type='application/json; charset=utf-8', filename=None):
        data = payload.encode('utf-8') if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def trusted_request(self):
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin')
        return host in allowed and (origin is None or origin in {'http://' + h for h in allowed})

    def do_GET(self):
        if not self.trusted_request():
            return self.send(403, {'error': 'Yalnızca yerel uygulama erişimi kabul edilir.'})
        path = urlsplit(self.path).path
        static = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path in static:
            name, mime = static[path]
            return self.send(200, (ROOT / 'static' / name).read_text(encoding='utf-8'), mime)
        if path == '/api/bootstrap':
            apps = storage.list_applications()
            return self.send(200, {'mode': MODE, 'as_of': AS_OF, 'disclaimer': DISCLAIMER,
                                  'applications': [{'id': a['id'], 'title': a['applicant']['title'],
                                                    'scenario': a['scenario']} for a in apps], 'policy': POLICY})
        if path == '/api/logs':
            return self.send(200, snapshot())
        match = re.fullmatch(r'/api/applications/([0-9]{4})(?:/(report|history|documents|export))?', path)
        if match:
            application_id, view = match.groups()
            try:
                app = storage.get_application(application_id)
                if view == 'report':
                    return self.send(200, storage.latest_report(application_id))
                if view == 'history':
                    return self.send(200, storage.history(application_id))
                if view == 'documents':
                    return self.send(200, storage.documents(application_id))
                if view == 'export':
                    report = storage.latest_report(application_id)
                    if not report:
                        raise ValueError('Henüz rapor yok.')
                    return self.send(200, service.markdown(report), 'text/markdown; charset=utf-8', f'basvuru-{application_id}.md')
                return self.send(200, {k: v for k, v in app.items() if k not in ('customer', 'customer_service_error')})
            except ValueError as exc:
                return self.send(404, {'error': str(exc)})
        self.send(404, {'error': 'Adres bulunamadı.'})

    def do_POST(self):
        if not self.trusted_request():
            return self.send(403, {'error': 'Geçersiz kaynak.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 3_000_000:
                raise ValueError('İstek boyutu geçersiz veya çok büyük.')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSON gövdesi gerekli.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('JSON nesnesi gerekli.')
            path = urlsplit(self.path).path
            with LOCK:
                if path == '/api/chat':
                    session_id = body.get('session_id', '')
                    if not isinstance(session_id, str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}', session_id):
                        raise ValueError('Geçersiz oturum.')
                    return self.send(200, service.chat(session_id, body.get('message'), body.get('application_id'), MODE))
                match = re.fullmatch(r'/api/applications/([0-9]{4})/(review|upload|attach-financial|remove-document)', path)
                if not match:
                    return self.send(404, {'error': 'Adres bulunamadı.'})
                application_id, action = match.groups()
                storage.get_application(application_id)
                if action == 'review':
                    return self.send(200, service.review(application_id, MODE))
                if action == 'remove-document':
                    storage.remove_document(application_id, body.get('document_id'))
                    return self.send(200, {'message': 'Belge silindi. Raporu güncellemek için yeniden inceleyin.'})
                if action == 'upload':
                    doc = ingest(application_id, body.get('name'), body.get('data'), body.get('kind'), body.get('issued_on'))
                    return self.send(201, {'document_id': doc['id'], 'message': 'Belge eklendi. Raporu güncellemek için yeniden inceleyin.'})
                if application_id != '1002':
                    raise ValueError('Bu dosyada eklenebilir mali tablo kaydı bulunmuyor.')
                docs = storage.documents(application_id)
                if any(d['kind'] == 'mali_tablo' for d in docs):
                    raise ValueError('Mali tablo zaten mevcut.')
                storage.add_document(application_id, document(storage.get_application(application_id), 'mali_tablo'))
                return self.send(201, {'message': 'Mali tablo eklendi. Yeniden inceleyebilirsiniz.'})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send(400, {'error': str(exc)})
        except RuntimeError as exc:
            self.send(503, {'error': str(exc)})
        except Exception as exc:
            LOGGER.error('İstek işlenemedi (%s)', type(exc).__name__)
            self.send(500, {'error': 'İşlem tamamlanamadı; mevcut kayıtlar korunuyor.'})


def serve(port=8765, open_browser=False):
    reset_session(console=True)
    try:
        discard_legacy_logs()
        return _serve(port, open_browser)
    finally:
        close_session()


@critical('server.run')
def _serve(port=8765, open_browser=False):
    seed()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = SessionLogHandler()
    LOGGER.addHandler(log)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    server = None
    worker = None
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        url = f'http://localhost:{server.server_port}'
        health_url = f'http://127.0.0.1:{server.server_port}/api/bootstrap'
        with build_opener(ProxyHandler({})).open(health_url, timeout=5) as response:
            if response.status != 200 or 'applications' not in json.load(response):
                raise OSError('Başlangıç HTTP kontrolü başarısız.')
        print(f'Kredi Dosyası | {url}', flush=True)
        print('HTTP kontrolü başarılı. Durdurmak için Ctrl+C.', flush=True)
        print(DISCLAIMER, flush=True)
        if open_browser:
            try:
                if not webbrowser.open(url):
                    print('Tarayıcı açılamadı; yukarıdaki adresi tarayıcıya yapıştırın.', flush=True)
            except OSError as exc:
                LOGGER.error('Tarayıcı açılamadı (%s)', type(exc).__name__)
                print('Tarayıcı açılamadı; yukarıdaki adresi tarayıcıya yapıştırın.', flush=True)
        while worker.is_alive():
            worker.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        LOGGER.error('Sunucu başlangıcı veya çalışması başarısız (%s)', type(exc).__name__)
        raise
    finally:
        if server is not None:
            if worker is not None and worker.is_alive():
                server.shutdown()
                worker.join(timeout=5)
            server.server_close()
        LOGGER.removeHandler(log)
        log.close()
