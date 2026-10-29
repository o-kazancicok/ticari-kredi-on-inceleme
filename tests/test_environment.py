import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kredi.environment import load_environment, validate_settings, check_environment


class EnvironmentTests(unittest.TestCase):
    def test_dotenv_respects_terminal_and_keeps_literal_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('KREDI_MODE=agent\nLOCAL_VALUE=${DO_NOT_EXPAND}\n', encoding='utf-8')
            with patch.dict(os.environ, {'KREDI_MODE': 'demo'}, clear=True):
                load_environment(path)
                self.assertEqual(os.environ['KREDI_MODE'], 'demo')
                self.assertEqual(os.environ['LOCAL_VALUE'], '${DO_NOT_EXPAND}')

    def test_invalid_settings_fail_with_actionable_messages(self):
        for settings in ({'KREDI_MODE': 'invalid'}, {'KREDI_ENGINE': 'invalid'},
                         {'KREDI_PORT': 'zero'}, {'KREDI_PORT': '0'}, {'KREDI_PORT': '65536'},
                         {'KREDI_MODE': 'agent', 'OLLAMA_URL': 'https://remote.invalid'},
                         {'KREDI_MODE': 'agent', 'OLLAMA_URL': 'http://user:pass@localhost:11434'},
                         {'KREDI_MODE': 'agent', 'OLLAMA_URL': 'http://localhost:bad'},
                         {'KREDI_MODE': 'agent', 'OLLAMA_MODEL': ''}):
            with self.subTest(settings=settings), patch.dict(os.environ, settings, clear=True):
                with self.assertRaises(ValueError):
                    validate_settings()

    def test_demo_checks_never_contact_ollama(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'KREDI_MODE': 'demo', 'KREDI_DATA_DIR': directory}, clear=True):
                with patch('kredi.environment.build_opener') as network:
                    ok, messages = check_environment()
                self.assertTrue(ok, messages)
                network.assert_not_called()
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_agent_requires_selected_model_and_handles_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = {'KREDI_MODE': 'agent', 'KREDI_DATA_DIR': directory,
                        'OLLAMA_MODEL': 'required-model:4b'}
            with patch.dict(os.environ, settings, clear=True):
                with patch('kredi.environment.build_opener') as opener:
                    opener.return_value.open.side_effect = OSError('offline')
                    self.assertFalse(check_environment()[0])
                for model, expected in [('different:4b', False), ('required-model:4b', True)]:
                    with patch('kredi.environment.build_opener') as opener:
                        response = io.BytesIO(json.dumps({'models': [{'name': model}]}).encode())
                        opener.return_value.open.return_value.__enter__.return_value = response
                        self.assertEqual(check_environment()[0], expected)

    def test_unwritable_data_directory_is_reported(self):
        with patch.dict(os.environ, {'KREDI_MODE': 'demo'}, clear=True):
            with patch('kredi.environment.Path.mkdir', side_effect=PermissionError()):
                ok, messages = check_environment()
        self.assertFalse(ok)
        self.assertIn('Veri dizinine yazılamıyor', messages[-1])
