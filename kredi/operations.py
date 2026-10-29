"""Selective JSON operation logs without request, document or model contents."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone, timedelta
from functools import wraps
from collections import deque
import inspect
import logging
from pathlib import Path
import re
import sys
import threading
import time
import uuid

_trace = ContextVar('operation_trace', default=None)
_operation = ContextVar('operation_id', default=None)
_application = ContextVar('operation_application', default=None)
_lock = threading.RLock()
_records = deque(maxlen=2000)
_session_id = uuid.uuid4().hex
_enabled = True
_console_enabled = False


def reset_session(console=False):
    global _session_id, _enabled, _console_enabled
    with _lock:
        _records.clear()
        _session_id = uuid.uuid4().hex
        _enabled = True
        _console_enabled = console


def close_session():
    global _enabled, _console_enabled
    with _lock:
        _enabled = False
        _console_enabled = False
        _records.clear()


def snapshot():
    with _lock:
        return {'session_id': _session_id, 'capacity': _records.maxlen,
                'records': [dict(row) for row in _records]}


def discard_legacy_logs():
    from .storage import DB_PATH
    root = Path(DB_PATH).parent.resolve()
    for stem in ('operations.log', 'server.log'):
        for suffix in ('', '.1', '.2', '.3'):
            path = root / (stem + suffix)
            if path.parent.resolve() != root:
                raise ValueError('Günlük dosyası veri klasörünün dışında.')
            try:
                path.unlink(missing_ok=True)
            except OSError:
                _write('server.diagnostic', 'warning', logging.WARNING,
                       {'message': 'Eski günlük dosyası silinemedi. Önceki uygulama oturumunu kapatın.'})


class SessionLogHandler(logging.Handler):
    def emit(self, record):
        _write('server.diagnostic', 'failed' if record.levelno >= logging.ERROR else 'warning',
               record.levelno, {'message': record.getMessage()})


def _print_terminal(row):
    local = datetime.fromisoformat(row['time']).astimezone(timezone(timedelta(hours=3)))
    phases = {'started': 'BASLADI', 'completed': 'TAMAMLANDI', 'failed': 'HATA', 'warning': 'UYARI'}
    parts = [local.strftime('%H:%M:%S'), row['level'], row['event'], phases.get(row['phase'], row['phase'])]
    for key, label in (('application_id', 'basvuru'), ('trace_id', 'takip'),
                       ('duration_ms', 'sure_ms'), ('error_type', 'hata'),
                       ('report_id', 'rapor'), ('tool_call_count', 'arac_sayisi'), ('outcome', 'sonuc')):
        if row.get(key) is not None:
            parts.append(f'{label}={row[key]}')
    if row.get('message'):
        parts.append(row['message'].replace('\n', r'\n').replace('\r', r'\r'))
    text = ' | '.join(parts)
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    text = text.encode(encoding, errors='backslashreplace').decode(encoding)
    try:
        print(text, flush=True)
    except OSError:
        pass  # Closing the terminal must not turn a completed operation into a failure.


def _write(event, phase, level, fields):
    row = {'time': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
           'level': logging.getLevelName(level), 'event': event, 'phase': phase,
           'trace_id': _trace.get(), 'operation_id': _operation.get(), **fields}
    with _lock:
        if _enabled:
            _records.append(row)
            if _console_enabled:
                _print_terminal(row)


@contextmanager
def operation(event, application_id=None, **metadata):
    parent = _operation.get()
    candidate = str(application_id) if application_id is not None else _application.get()
    app_id = candidate if candidate and re.fullmatch(r'[0-9]{4}', candidate) else None
    tokens = (_trace.set(_trace.get() or uuid.uuid4().hex),
              _operation.set(uuid.uuid4().hex), _application.set(app_id))
    fields = {'parent_operation_id': parent, 'application_id': app_id}
    # Values come from fixed enumerations; unvalidated strings never enter the log.
    allowed = {'mode': {'demo', 'agent'},
               'kind': {'vergi_levhasi', 'faaliyet_belgesi', 'mali_tablo'}}
    for key, values in allowed.items():
        if isinstance(metadata.get(key), str) and metadata[key] in values:
            fields[key] = metadata[key]
    summary = {}
    started = time.monotonic()
    try:
        _write(event, 'started', logging.INFO, fields)
        try:
            yield summary
        except Exception as exc:
            _write(event, 'failed', logging.ERROR,
                   fields | {'duration_ms': round((time.monotonic()-started)*1000, 2),
                             'error_type': type(exc).__name__,
                             'cause_type': type(exc.__cause__).__name__ if exc.__cause__ else None})
            raise
        else:
            safe_summary = {k: v for k, v in summary.items()
                            if k in {'report_id', 'control_count', 'open_task_count', 'tool_call_count'}
                            and isinstance(v, int) and not isinstance(v, bool)}
            if summary.get('outcome') in ('available', 'unavailable'):
                safe_summary['outcome'] = summary['outcome']
            level = logging.WARNING if summary.get('outcome') == 'unavailable' else logging.INFO
            _write(event, 'completed', level,
                   fields | safe_summary | {'duration_ms': round((time.monotonic()-started)*1000, 2)})
    finally:
        _application.reset(tokens[2])
        _operation.reset(tokens[1])
        _trace.reset(tokens[0])


def critical(event, application_param=None, fields=()):
    def decorate(function):
        signature = inspect.signature(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            arguments = signature.bind(*args, **kwargs)
            arguments.apply_defaults()
            candidate = arguments.arguments.get(application_param)
            if isinstance(candidate, dict):
                candidate = candidate.get('application_id')
            metadata = {key: arguments.arguments.get(key) for key in fields}
            with operation(event, candidate, **metadata) as summary:
                result = function(*args, **kwargs)
                if isinstance(result, dict):
                    if isinstance(result.get('report_id'), int):
                        summary['report_id'] = result['report_id']
                    for source, target in (('findings', 'control_count'), ('tasks', 'open_task_count'),
                                           ('tool_calls', 'tool_call_count')):
                        if isinstance(result.get(source), list):
                            summary[target] = len(result[source])
                return result
        return wrapped
    return decorate
