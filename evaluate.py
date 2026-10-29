"""Reproducible synthetic baseline evaluation, not evidence of bank ROI."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from kredi import storage
from kredi.seed import seed, document
from kredi.service import review

EXPECTED = {'1001': {}, '1002': {'document_mali_tablo': 'eksik'},
            '1003': {'title': 'dogrulama_gerekli'}, '1004': {'guarantor': 'eksik'},
            '1005': {key: 'kontrol_edilemedi' for key in ['title', 'tax_id', 'legal_form', 'foundation_date', 'sector', 'address']}}


def evaluate():
    test_root = Path(__file__).resolve().parent / 'runtime' / 'evaluation'
    test_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=test_root) as directory, patch.object(storage, 'DB_PATH', Path(directory) / 'eval.db'):
        seed()
        cases, tp, fp, fn, sourced, total = [], 0, 0, 0, 0, 0
        for app_id, expected in EXPECTED.items():
            report = review(app_id, mode='demo')
            actual = {f['id']: f['status'] for f in report['findings'] if f['status'] != 'uygun'}
            wanted, got = set(expected.items()), set(actual.items())
            tp += len(wanted & got)
            fp += len(got - wanted)
            fn += len(wanted - got)
            total += len(report['findings'])
            sourced += sum(bool(f['evidence'] and f['policy_source']) for f in report['findings'])
            cases.append({'application_id': app_id, 'expected': expected, 'actual': actual,
                          'passed': actual == expected, 'report_status': report['status']})
        first = review('1002', mode='demo')
        storage.add_document('1002', document(storage.get_application('1002'), 'mali_tablo'))
        resumed = review('1002', mode='demo')
        return {'dataset': 'five-handcrafted-synthetic-cases-v1', 'mode': 'deterministic-demo',
                'warning': 'Not an LLM quality benchmark, not a bank pilot. Small authored dataset; no real-world generalization claim.',
                'cases': cases, 'issue_precision': tp / (tp + fp) if tp + fp else 1,
                'issue_recall': tp / (tp + fn) if tp + fn else 1,
                'source_presence_coverage': sourced / total,
                'source_presence_note': 'Measures reference presence only; not independent source truth verification.',
                'resume_passed': not resumed['tasks'] and resumed['previous_report_id'] == first['report_id'],
                'resume_changes': resumed['changes'], 'real_model_tested': False,
                'measured_time_saving': None}


if __name__ == '__main__':
    result = evaluate()
    destination = Path(__file__).parent / 'docs' / 'evaluation.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
