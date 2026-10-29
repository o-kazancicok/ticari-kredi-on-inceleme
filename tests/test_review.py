import base64
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Unit tests stay deterministic even when the local application uses a real model.
# Real-model integration checks are run separately by scripts/verify_agent.py.
os.environ['KREDI_MODE'] = 'demo'
os.environ['KREDI_ENGINE'] = 'native'

from kredi import storage
from kredi.seed import seed, document
from kredi.service import review, chat
from kredi.checks import select_sector, identity, documents
from kredi.tools import ReviewTools
from kredi.agent import run_agent
from kredi.documents import ingest
from kredi.policy import search_policy


class ReviewTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parent.parent / 'runtime' / 'tests'
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        self.db_patch = patch.object(storage, 'DB_PATH', Path(self.temp.name) / 'test.sqlite3')
        self.db_patch.start()
        seed()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_complete_application_has_evidence_for_every_finding(self):
        r = review('1001')
        self.assertEqual(r['status'], 'uzman_incelemesine_hazir')
        self.assertEqual(r['counts'], {'uygun': 13})
        self.assertTrue(all(f['evidence'] and f['policy_source'] for f in r['findings']))

    def test_five_scenarios_match_expected_findings_exactly(self):
        expected = {
            '1001': {}, '1002': {'document_mali_tablo': 'eksik'},
            '1003': {'title': 'dogrulama_gerekli'}, '1004': {'guarantor': 'eksik'},
            '1005': {key: 'kontrol_edilemedi' for key in
                     ['title', 'tax_id', 'legal_form', 'foundation_date', 'sector', 'address']},
        }
        for app_id, wanted in expected.items():
            with self.subTest(app_id=app_id):
                r = review(app_id)
                actual = {f['id']: f['status'] for f in r['findings'] if f['status'] != 'uygun'}
                self.assertEqual(actual, wanted)

    def test_resume_changes_only_missing_document_and_preserves_history(self):
        before = review('1002')
        storage.add_document('1002', document(storage.get_application('1002'), 'mali_tablo'))
        after = review('1002')
        self.assertEqual(after['changes'], [{'id': 'document_mali_tablo', 'label': 'mali_tablo',
                                           'before': 'eksik', 'after': 'uygun'}])
        self.assertEqual(after['previous_report_id'], before['report_id'])
        self.assertEqual(after['tasks'], [])
        self.assertGreaterEqual(len(storage.history('1002')), 5)

    def test_customer_outage_never_becomes_ready(self):
        r = review('1005')
        self.assertNotEqual(r['status'], 'uzman_incelemesine_hazir')
        self.assertEqual(r['counts']['kontrol_edilemedi'], 6)

    def test_sector_priority_highest_tie_and_bad_total(self):
        a = {'code': 'A', 'percent': '40'}
        b = {'code': 'B', 'percent': '60'}
        self.assertEqual(select_sector([a, b]), b)
        priority = {'code': 'C', 'percent': '-'}
        self.assertEqual(select_sector([a, priority]), priority)
        self.assertEqual(select_sector([priority]), priority)
        for invalid in [[dict(a, percent='50'), dict(b, percent='50')],
                        [dict(a, percent='-'), priority],
                        [dict(a, percent='10'), b], [dict(a, percent='NaN'), b],
                        [dict(a, percent='oops'), b]]:
            with self.assertRaises(ValueError):
                select_sector(invalid)

    def test_nace_format_matches_without_hiding_different_codes(self):
        from kredi.checks import activity
        app = storage.get_application('1001')
        results = activity(app, app['customer'], storage.documents('1001'), '2026-10-17')
        self.assertTrue(all(f['status'] == 'uygun' for f in results))
        app['applicant']['nace'] = '463102'
        result = activity(app, app['customer'], [], '2026-10-17')
        self.assertEqual(next(f for f in result if f['id'] == 'nace')['status'], 'dogrulama_gerekli')

    def test_expired_future_bad_date_and_unreadable_documents(self):
        app = storage.get_application('1001')
        for raw, readable, expected in [('2026-01-01', True, 'dogrulama_gerekli'),
                                        ('2027-01-01', True, 'dogrulama_gerekli'),
                                        ('not-a-date', True, 'dogrulama_gerekli'),
                                        ('2026-10-01', False, 'kontrol_edilemedi')]:
            docs = storage.documents('1001')
            docs[0].update(issued_on=raw, readable=readable)
            result = documents(app, app['customer'], docs, '2026-10-17')
            item = next(f for f in result if f['id'] == 'document_' + docs[0]['kind'])
            self.assertEqual(item['status'], expected)

    def test_company_age_calendar_boundary(self):
        app = storage.get_application('1001')
        app['applicant']['foundation_date'] = '2025-10-18'
        item = identity(app, app['customer'], storage.documents('1001'), '2026-10-17')[-1]
        self.assertEqual(item['status'], 'dogrulama_gerekli')
        app['applicant']['foundation_date'] = '2025-10-17'
        self.assertEqual(identity(app, app['customer'], [], '2026-10-17')[-1]['status'], 'uygun')

    def test_scope_preconditions_and_document_access(self):
        tools = ReviewTools('1001')
        for name, args in [('delete_application', {}), ('get_application', {'application_id': '1002'}),
                           ('check_identity', {}), ('read_document', {'document_id': 'D-1002-vergi_levhasi-v1'})]:
            with self.assertRaises(ValueError):
                tools.call(name, args)
        self.assertTrue(tools.call('search_policy', {'query': 'belge tarihi'}))

    def test_chat_remembers_application_without_repeating_id(self):
        chat('test-session', '1002 başvurusunu incele')
        answer = chat('test-session', 'Eksikleri göster')
        self.assertIn('mali_tablo', answer['message'])
        self.assertEqual(storage.session('test-session')['application_id'], '1002')

    def test_chat_blocks_unsupported_bulk_request(self):
        result = chat('test-session', 'Tüm müşterileri listele')
        self.assertEqual(result['guard'], 'blocked')

    def test_upload_then_resume(self):
        raw = 'EĞİTİM AMAÇLI SENTETİK MALİ TABLO\nUnvan: Güney Tarım Limited Şirketi'.encode()
        result = ingest('1002', '../../deneme.txt', base64.b64encode(raw).decode(), 'mali_tablo', '2026-10-01')
        self.assertEqual(result['name'], 'deneme.txt')
        self.assertEqual(review('1002')['tasks'], [])

    def test_upload_rejects_bad_format_and_ambiguous_fields(self):
        for name, data in [('bad.exe', b'x'), ('bad.txt', b'Unvan: A\nUnvan: B')]:
            with self.assertRaises(ValueError):
                ingest('1002', name, base64.b64encode(data).decode(), 'mali_tablo', '2026-10-01')
        with self.assertRaises(ValueError):
            ingest('1002', 'x.txt', '???', 'mali_tablo', '2026-10-01')

    def test_unsupported_product_fails_closed(self):
        app = storage.get_application('1001')
        app['product'] = 'UNKNOWN'
        with storage.connect() as db:
            db.execute('UPDATE applications SET payload=? WHERE id=?', (storage.dump(app), app['id']))
        with self.assertRaises(ValueError):
            review('1001')
        self.assertIsNone(storage.latest_report('1001'))

    def test_no_match_retrieval_returns_empty(self):
        self.assertEqual(search_policy('zzzzzzzzzz'), [])

    def test_native_agent_tool_loop_uses_observations_and_recovers(self):
        tools = ReviewTools('1003')
        batches = [
            ['check_identity'],  # deliberate precondition failure
            ['get_application', 'get_customer', 'get_documents', 'get_policy'],
            ['check_identity', 'check_activity', 'check_contact', 'check_guarantor', 'check_documents'],
            [('search_policy', {'query': 'firma unvanı'})],
            [],
        ]
        calls = []
        def fake(messages, schemas):
            calls.append(copy.deepcopy(messages))
            batch = batches.pop(0)
            return {'role': 'assistant', 'content': '', 'tool_calls': [
                {'function': {'name': item[0] if isinstance(item, tuple) else item,
                              'arguments': item[1] if isinstance(item, tuple) else {}}} for item in batch]}
        run_agent(tools, client=fake, engine='native')
        self.assertTrue(tools.complete())
        self.assertEqual(tools.trace[0]['status'], 'rejected')
        self.assertTrue(any('error' in m.get('content', '') for m in calls[1] if m['role'] == 'tool'))
        self.assertEqual(next(i for i in tools.findings() if i['id'] == 'title')['status'], 'dogrulama_gerekli')

    def test_agent_noncompletion_is_bounded(self):
        tools = ReviewTools('1001')
        def fake(messages, schemas):
            return {'role': 'assistant', 'content': 'Bitti', 'tool_calls': []}
        with self.assertRaises(RuntimeError):
            run_agent(tools, client=fake, engine='native')
        self.assertFalse(tools.complete())

    def test_remove_wrong_upload_restores_previous_document_and_preserves_report(self):
        good = review('1001')
        bad_doc = document(storage.get_application('1001'), 'vergi_levhasi', suffix='wrong-upload')
        bad_doc['fields']['tax_id'] = '9999999999'
        storage.add_document('1001', bad_doc)
        self.assertTrue(storage.latest_report('1001')['documents_changed'])
        bad_report = review('1001')
        self.assertFalse(storage.latest_report('1001')['documents_changed'])
        self.assertEqual(next(f for f in bad_report['findings'] if f['id'] == 'tax_id')['status'], 'dogrulama_gerekli')
        storage.remove_document('1001', bad_doc['id'])
        self.assertNotIn(bad_doc['id'], [d['id'] for d in storage.documents('1001')])
        retained = storage.latest_report('1001')
        self.assertEqual(retained['report_id'], bad_report['report_id'])
        self.assertEqual(retained['findings'], bad_report['findings'])
        self.assertTrue(retained['documents_changed'])
        from kredi.service import markdown
        self.assertIn('önceki belge kümesine', markdown(retained))
        fresh = review('1001')
        self.assertEqual(fresh['counts'], good['counts'])
        self.assertFalse(storage.latest_report('1001')['documents_changed'])
        removed = next(e for e in storage.history('1001') if e['kind'] == 'document_removed')
        self.assertEqual(removed['payload']['document_id'], bad_doc['id'])

    def test_remove_document_is_scoped_and_rejects_repeat_or_invalid_ids(self):
        doc_id = storage.documents('1001')[0]['id']
        before = storage.documents('1001')
        for app_id, value in [('1002', doc_id), ('9999', doc_id), ('1001', None),
                              ('1001', []), ('1001', ''), ('1001', 'x' * 161),
                              ('1001', "' OR 1=1 --")]:
            with self.subTest(app_id=app_id, value=value), self.assertRaises(ValueError):
                storage.remove_document(app_id, value)
        self.assertEqual(storage.documents('1001'), before)
        storage.remove_document('1001', doc_id)
        with self.assertRaises(ValueError):
            storage.remove_document('1001', doc_id)

    def test_removal_persists_after_restart_and_required_document_becomes_missing(self):
        doc_id = next(d['id'] for d in storage.documents('1001') if d['kind'] == 'mali_tablo')
        storage.remove_document('1001', doc_id)
        seed()
        report = review('1001')
        self.assertEqual(next(f for f in report['findings'] if f['id'] == 'document_mali_tablo')['status'], 'eksik')

    def test_remove_document_rolls_back_if_history_write_fails(self):
        doc_id = storage.documents('1001')[0]['id']
        with patch('kredi.storage.dump', side_effect=RuntimeError('write failed')):
            with self.assertRaises(RuntimeError):
                storage.remove_document('1001', doc_id)
        self.assertIn(doc_id, [d['id'] for d in storage.documents('1001')])

    def test_unknown_application(self):
        with self.assertRaises(ValueError):
            review('9999')


if __name__ == '__main__':
    unittest.main()
