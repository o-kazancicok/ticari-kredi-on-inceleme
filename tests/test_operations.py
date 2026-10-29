import base64
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
from collections import deque
import sqlite3
import unittest
from unittest.mock import patch

import test_review
from kredi import storage, service, operations
from kredi.agent import ollama_chat
from kredi.documents import ingest


class OperationLoggingTests(unittest.TestCase):
    def setUp(self):
        test_review.ReviewTests.setUp(self)
        operations.reset_session()

    tearDown = test_review.ReviewTests.tearDown

    def records(self):
        return operations.snapshot()['records']

    def log_text(self):
        return json.dumps(self.records())

    def test_start_is_written_before_save_and_nested_steps_share_trace(self):
        original = storage.save_report

        def verify_before_write(report):
            rows = self.records()
            self.assertTrue(any(r['event'] == 'review.run' and r['phase'] == 'started' for r in rows))
            self.assertFalse(any(r['event'] == 'review.run' and r['phase'] == 'completed' for r in rows))
            return original(report)

        with patch.object(storage, 'save_report', side_effect=verify_before_write):
            report = service.review('1001', mode='demo')
        rows = self.records()
        self.assertEqual(len({r['trace_id'] for r in rows}), 1)
        self.assertEqual({r['application_id'] for r in rows}, {'1001'})
        outer = rows[0]['operation_id']
        saved = next(r for r in rows if r['event'] == 'report.save' and r['phase'] == 'completed')
        self.assertEqual(saved['parent_operation_id'], outer)
        self.assertEqual(saved['report_id'], report['report_id'])
        self.assertEqual(rows[-1]['phase'], 'completed')

    def test_failed_database_write_has_start_and_failure_without_error_payload(self):
        with patch.object(storage, 'connect', side_effect=sqlite3.OperationalError('SECRET_DB_PAYLOAD')):
            with self.assertRaises(sqlite3.OperationalError):
                storage.save_report({'application_id': '1002', 'title': 'SECRET_COMPANY'})
        rows = self.records()
        self.assertEqual([r['phase'] for r in rows], ['started', 'failed'])
        self.assertEqual(rows[-1]['error_type'], 'OperationalError')
        self.assertNotIn('SECRET', self.log_text())

    def test_invalid_upload_does_not_log_filename_body_or_encoded_data(self):
        body = base64.b64encode(b'SECRET_DOCUMENT_CONTENT').decode()
        with self.assertRaises(ValueError):
            ingest('1002', 'SECRET_CUSTOMER.exe', body, 'mali_tablo', '2026-10-01')
        text = self.log_text()
        self.assertNotIn('SECRET', text)
        self.assertNotIn(body, text)
        self.assertEqual(self.records()[-1]['phase'], 'failed')

    def test_concurrent_applications_keep_separate_traces(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda app: service.review(app, mode='demo'), ['1001', '1002', '1003', '1004']))
        traces = {}
        for row in self.records():
            traces.setdefault(row['trace_id'], set()).add(row['application_id'])
        self.assertEqual(len(traces), 4)
        self.assertTrue(all(len(apps) == 1 for apps in traces.values()))

    def test_session_buffer_is_bounded_and_cleared_on_close(self):
        with patch.object(operations, '_records', deque(maxlen=6)):
            for app in ['1001', '1002', '1003']:
                service.review(app, mode='demo')
            self.assertEqual(len(self.records()), 6)
            previous = operations.snapshot()['session_id']
            operations.close_session()
            self.assertEqual(self.records(), [])
            with operations.operation('late.background'):
                pass
            self.assertEqual(self.records(), [])
            operations.reset_session()
            self.assertNotEqual(previous, operations.snapshot()['session_id'])
            self.assertEqual(self.records(), [])

    def test_model_request_inherits_application_but_logs_no_messages_or_output(self):
        response = {'message': {'role': 'assistant', 'content': 'SECRET_MODEL_OUTPUT',
                               'tool_calls': [{'function': {'name': 'get_application', 'arguments': {}}}]}}
        with patch('kredi.agent.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = io.BytesIO(json.dumps(response).encode())
            with operations.operation('review.run', '1002'):
                result = ollama_chat([{'role': 'user', 'content': 'SECRET_PROMPT'}])
        self.assertEqual(result['content'], 'SECRET_MODEL_OUTPUT')
        rows = self.records()
        model = next(r for r in rows if r['event'] == 'model.request' and r['phase'] == 'completed')
        self.assertEqual(model['application_id'], '1002')
        self.assertEqual(model['tool_call_count'], 1)
        self.assertEqual(len({r['trace_id'] for r in rows}), 1)
        self.assertNotIn('SECRET', self.log_text())

    def test_server_session_clears_logs_on_normal_and_failed_shutdown(self):
        from kredi import web
        (Path(self.temp.name) / 'server.log').write_text('old operational log', encoding='utf-8')

        def session_work(*args):
            with operations.operation('review.run', '1001'):
                pass
            self.assertTrue(self.records())

        with patch.object(web, '_serve', side_effect=session_work):
            web.serve()
        self.assertEqual(self.records(), [])
        with patch.object(web, '_serve', side_effect=RuntimeError('SECRET_STARTUP')):
            with self.assertRaises(RuntimeError):
                web.serve()
        self.assertEqual(self.records(), [])
        self.assertEqual(list(Path(self.temp.name).rglob('*.log*')), [])

    def test_terminal_prints_before_operation_and_on_failure_without_payload(self):
        with patch('sys.stdout', new_callable=io.StringIO) as terminal:
            operations.reset_session(console=True)
            with self.assertRaises(ValueError):
                with operations.operation('review.run', '1002'):
                    self.assertIn('BASLADI', terminal.getvalue())
                    raise ValueError('SECRET_CUSTOMER_DATA')
            output = terminal.getvalue()
            self.assertIn('HATA', output)
            self.assertIn('basvuru=1002', output)
            self.assertIn('hata=ValueError', output)
            self.assertNotIn('SECRET', output)
            operations.close_session()
            with operations.operation('late.background'):
                pass
            self.assertEqual(output, terminal.getvalue())
        operations.reset_session()
