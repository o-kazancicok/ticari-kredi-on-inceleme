"""Compare real local model reviews with the baseline in a temporary database."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kredi import storage, service
from kredi.agent import run_agent, ollama_chat
from kredi.config import MODEL, DATA_DIR, OLLAMA_URL
from kredi.seed import seed, document


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--applications', nargs='+', default=['1001', '1002', '1003', '1004', '1005'])
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = {'model': MODEL, 'engine': 'native', 'started_at': storage.now(),
              'applications': [], 'resume': None, 'passed': False}
    output = DATA_DIR / 'agent-verification.json'

    def tracked_client(messages, tools=None):
        started = time.monotonic()
        response = ollama_chat(messages, tools)
        calls = [call.get('function', {}).get('name', '?') for call in response.get('tool_calls', [])]
        print(f'  Model turn: {time.monotonic()-started:.1f}s; tools: {", ".join(calls) or "completed response"}', flush=True)
        return response

    def real_agent(tools):
        return run_agent(tools, client=tracked_client, engine='native')

    def signature(report):
        return {finding['id']: finding['status'] for finding in report['findings']}

    with tempfile.TemporaryDirectory(prefix='agent-test-', dir=DATA_DIR) as scratch:
        with patch.object(storage, 'DB_PATH', Path(scratch) / 'checks.sqlite3'):
            seed()
            for app_id in args.applications:
                print(f'Application {app_id}: real LLM review...', flush=True)
                started = time.monotonic()
                baseline = service.review(app_id, mode='demo')
                entry = {'application_id': app_id, 'passed': False}
                try:
                    with patch.object(service, 'run_agent', real_agent):
                        report = service.review(app_id, mode='agent')
                    entry.update(passed=signature(report) == signature(baseline),
                                 counts=report['counts'], trace_steps=len(report['trace']),
                                 rejected_calls=sum(t['status'] == 'rejected' for t in report['trace']))
                except Exception as exc:
                    entry['error'] = str(exc)
                entry['seconds'] = round(time.monotonic() - started, 2)
                result['applications'].append(entry)
                output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'  {app_id}: {"PASS" if entry["passed"] else "FAIL"} ({entry["seconds"]}s)', flush=True)
            if '1002' in args.applications:
                print('Application 1002: attach missing document and resume...', flush=True)
                storage.add_document('1002', document(storage.get_application('1002'), 'mali_tablo'))
                try:
                    with patch.object(service, 'run_agent', real_agent):
                        report = service.review('1002', mode='agent')
                    result['resume'] = {'passed': not report['tasks'], 'counts': report['counts']}
                except Exception as exc:
                    result['resume'] = {'passed': False, 'error': str(exc)}
    result['passed'] = (all(entry['passed'] for entry in result['applications'])
                        and (result['resume'] is None or result['resume']['passed']))
    result['completed_at'] = storage.now()
    try:
        with build_opener(ProxyHandler({})).open(OLLAMA_URL + '/api/ps', timeout=5) as response:
            running = json.load(response).get('models', [])
        result['runtime'] = [
            {key: item[key] for key in ('name', 'size', 'size_vram', 'context_length') if key in item}
            for item in running if item.get('name') == MODEL
        ]
    except (OSError, ValueError):
        result['runtime'] = []
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Agent verification: {"PASS" if result["passed"] else "FAIL"}', flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
