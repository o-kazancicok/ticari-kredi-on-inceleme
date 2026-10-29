import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ['KREDI_MODE'] = 'demo'
os.environ['KREDI_ENGINE'] = 'native'

from kredi import storage
from kredi.agent import run_agent, ollama_chat
from kredi.seed import seed
from kredi.service import review
from kredi.tools import ReviewTools


class ModelUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, 'DB_PATH', Path(self.temp.name) / 'test.sqlite3')
        self.db.start()
        seed()

    def tearDown(self):
        self.db.stop()
        self.temp.cleanup()

    def client(self, metrics):
        turns = iter([
            ['get_application', 'get_customer', 'get_documents', 'get_policy'],
            ['check_identity', 'check_activity', 'check_contact', 'check_guarantor', 'check_documents'],
            [],
        ])
        observations = []
        def call(messages, schemas):
            observations.extend(messages)
            names = next(turns)
            message = {'role': 'assistant', 'content': '', 'tool_calls': [
                {'function': {'name': name, 'arguments': {}}} for name in names]}
            if metrics is not None:
                message['_usage'] = next(metrics)
            return message
        return call, observations

    def test_multiple_turns_aggregate_and_persist_without_leaking_metadata(self):
        metrics = iter([dict(model='qwen3:4b', prompt_eval_count=i, eval_count=10,
                             total_duration=2_000_000_000, eval_duration=500_000_000)
                        for i in (100, 200, 300)])
        client, observations = self.client(metrics)
        def agent(tools):
            return run_agent(tools, client=client, engine='native')
        with patch('kredi.service.run_agent', side_effect=agent):
            report = review('1001', mode='agent')
        usage = report['model_usage']
        self.assertEqual(usage['models'], ['qwen3:4b'])
        self.assertEqual(usage['call_count'], 3)
        self.assertEqual(usage['input_tokens'], 600)
        self.assertEqual(usage['output_tokens'], 30)
        self.assertEqual(usage['total_tokens'], 630)
        self.assertEqual(usage['model_duration_ms'], 6000)
        self.assertEqual(usage['output_tokens_per_second'], 20)
        self.assertGreaterEqual(report['review_duration_ms'], 0)
        self.assertEqual(storage.latest_report('1001')['model_usage'], usage)
        self.assertFalse(any('_usage' in message for message in observations))

    def test_missing_or_partial_metrics_never_report_a_misleading_total(self):
        for measurements in (None, iter([
                {'model': 'qwen3:4b', 'prompt_eval_count': 100, 'eval_count': 10},
                {'model': 'qwen3:4b', 'prompt_eval_count': 200, 'eval_count': None},
                {'model': 'qwen3:4b', 'prompt_eval_count': 300, 'eval_count': -1}])):
            client, _ = self.client(measurements)
            usage = run_agent(ReviewTools('1001'), client=client, engine='native')
            self.assertEqual(usage['call_count'], 3)
            self.assertIsNone(usage['total_tokens'])
            self.assertIsNone(usage['output_tokens'])
            self.assertIsNone(usage['output_tokens_per_second'])

    def test_demo_has_no_model_usage(self):
        report = review('1001', mode='demo')
        self.assertIsNone(report['model_usage'])
        self.assertGreaterEqual(report['review_duration_ms'], 0)

    def test_ollama_retains_response_metrics(self):
        import json
        result = {'message': {'role': 'assistant', 'content': 'ok'},
                  'model': 'actual-model:tag', 'prompt_eval_count': 42, 'eval_count': 8,
                  'total_duration': 100, 'eval_duration': 50}
        opener = MagicMock()
        import io
        opener.open.return_value.__enter__.return_value = io.BytesIO(json.dumps(result).encode())
        with patch('kredi.agent.urllib.request.build_opener', return_value=opener):
            message = ollama_chat([], model='requested-model')
        self.assertEqual(message['_usage']['model'], 'actual-model:tag')
        self.assertEqual(message['_usage']['prompt_eval_count'], 42)
        self.assertEqual(message['_usage']['eval_count'], 8)
