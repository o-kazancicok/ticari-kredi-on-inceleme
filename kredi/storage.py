"""SQLite transactions and durable application history. No arbitrary SQL tool."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import DB_PATH
from .operations import critical


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS applications(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY, application_id TEXT NOT NULL, kind TEXT NOT NULL,
          payload TEXT NOT NULL, added_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reports(
          id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL,
          payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL,
          kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
          id TEXT PRIMARY KEY, application_id TEXT, messages TEXT NOT NULL);
        ''')


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def list_applications():
    with connect() as db:
        return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM applications ORDER BY id')]


def get_application(application_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM applications WHERE id=?', (application_id,)).fetchone()
    if row is None:
        raise ValueError('Başvuru bulunamadı.')
    return json.loads(row['payload'])


def documents(application_id):
    with connect() as db:
        return [json.loads(r['payload']) for r in db.execute(
            'SELECT payload FROM documents WHERE application_id=? ORDER BY added_at,id', (application_id,))]


@critical('document.save', 'application_id')
def add_document(application_id, doc):
    get_application(application_id)
    with connect() as db:
        db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',
                   (doc['id'], application_id, doc['kind'], dump(doc), now()))
        db.execute('INSERT INTO events(application_id,kind,payload,created_at) VALUES(?,?,?,?)',
                   (application_id, 'document_added', dump({'document_id': doc['id'], 'kind': doc['kind']}), now()))


@critical('document.remove', 'application_id')
def remove_document(application_id, document_id):
    get_application(application_id)
    if not isinstance(document_id, str) or not 1 <= len(document_id) <= 160:
        raise ValueError('Geçersiz belge kimliği.')
    with connect() as db:
        row = db.execute('SELECT kind FROM documents WHERE application_id=? AND id=?',
                         (application_id, document_id)).fetchone()
        if row is None:
            raise ValueError('Belge bu başvuruda bulunamadı veya daha önce silindi.')
        db.execute('DELETE FROM documents WHERE application_id=? AND id=?',
                   (application_id, document_id))
        db.execute('INSERT INTO events(application_id,kind,payload,created_at) VALUES(?,?,?,?)',
                   (application_id, 'document_removed',
                    dump({'document_id': document_id, 'kind': row['kind']}), now()))


@critical('report.save', 'report')
def save_report(report):
    with connect() as db:
        row = db.execute('INSERT INTO reports(application_id,payload,created_at) VALUES(?,?,?)',
                         (report['application_id'], dump(report), now()))
        report['report_id'] = row.lastrowid
        db.execute('UPDATE reports SET payload=? WHERE id=?', (dump(report), report['report_id']))
        db.execute('INSERT INTO events(application_id,kind,payload,created_at) VALUES(?,?,?,?)',
                   (report['application_id'], 'review_completed', dump({'report_id': report['report_id'],
                    'status': report['status'], 'mode': report['mode']}), now()))
    return report


def latest_report(application_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM reports WHERE application_id=? ORDER BY id DESC LIMIT 1',
                         (application_id,)).fetchone()
        if row:
            events = db.execute('SELECT kind, MAX(id) AS last_id FROM events WHERE application_id=? '
                                'GROUP BY kind', (application_id,)).fetchall()
    if row is None:
        return None
    report = json.loads(row['payload'])
    last = {event['kind']: event['last_id'] for event in events}
    report['documents_changed'] = max(last.get('document_added', 0), last.get('document_removed', 0)) > last.get('review_completed', 0)
    return report


def history(application_id):
    with connect() as db:
        return [dict(r) | {'payload': json.loads(r['payload'])} for r in db.execute(
            'SELECT id,kind,payload,created_at FROM events WHERE application_id=? ORDER BY id DESC LIMIT 30',
            (application_id,))]


def session(session_id):
    with connect() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
    return {'application_id': row['application_id'], 'messages': json.loads(row['messages'])} if row else {
        'application_id': None, 'messages': []}


def save_session(session_id, value):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',
                   (session_id, value['application_id'], dump(value['messages'][-20:])))
