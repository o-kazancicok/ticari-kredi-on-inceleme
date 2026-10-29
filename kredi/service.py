import re
import time
from collections import Counter
from . import storage
from .config import AS_OF, MODE, DISCLAIMER
from .policy import POLICY, search_policy, normalize
from .tools import ReviewTools
from .agent import run_demo, run_agent
from .operations import critical


@critical('review.run', 'application_id', fields=('mode',))
def review(application_id, mode=MODE, as_of=AS_OF):
    if mode not in ('demo', 'agent'):
        raise ValueError('Çalışma modu demo veya agent olmalıdır.')
    started = time.perf_counter()
    app = storage.get_application(application_id)
    if app['product'] != POLICY['id']:
        raise ValueError('Bu ürün için sürümlü prosedür tanımlanmamış; inceleme başlatılamaz.')
    previous = storage.latest_report(application_id)
    tools = ReviewTools(application_id, as_of)
    model_usage = (run_demo if mode == 'demo' else run_agent)(tools)
    items = tools.findings()
    if not tools.complete() or any(not i['evidence'] or not i['policy_source'] for i in items):
        raise RuntimeError('Eksik kontrol veya kaynaksız bulgu; rapor oluşturulmadı.')
    counts = dict(Counter(i['status'] for i in items))
    blockers = [i for i in items if i['status'] not in ('uygun', 'uygulanamaz')]
    old = {i['id']: i for i in previous['findings']} if previous else {}
    changes = [{'id': i['id'], 'label': i['label'], 'before': old[i['id']]['status'], 'after': i['status']}
               for i in items if i['id'] in old and old[i['id']]['status'] != i['status']]
    return storage.save_report({
        'application_id': application_id, 'title': app['applicant']['title'], 'as_of': as_of,
        'mode': mode, 'disclaimer': DISCLAIMER, 'policy_id': POLICY['id'], 'policy_version': POLICY['version'],
        'status': 'tamamlanmasi_gereken_isler_var' if blockers else 'uzman_incelemesine_hazir',
        'findings': items, 'counts': counts,
        'tasks': [{'finding_id': i['id'], 'label': i['label'], 'action': i['action']} for i in blockers],
        'trace': tools.trace, 'changes': changes,
        'model_usage': model_usage,
        'review_duration_ms': round((time.perf_counter() - started) * 1000, 2),
        'previous_report_id': previous.get('report_id') if previous else None,
        'created_at': storage.now(),
    })


@critical('report.export', 'report')
def markdown(report):
    labels = {'uygun': 'Uygun', 'eksik': 'Eksik', 'dogrulama_gerekli': 'Doğrulama gerekli',
              'kontrol_edilemedi': 'Kontrol edilemedi', 'uygulanamaz': 'Uygulanamaz'}
    lines = [f"# Başvuru {report['application_id']} — Ön inceleme", '', report['disclaimer'], '',
             f"İnceleme tarihi: {report['as_of']} | Prosedür: {report['policy_id']} v{report['policy_version']}",
             f"Durum: {report['status']}", '']
    if report.get('documents_changed'):
        lines += ['UYARI: Belgeler değişti. Bu rapor önceki belge kümesine aittir; yeniden inceleme gereklidir.', '']
    for item in report['findings']:
        lines += [f"## {item['label']} — {labels[item['status']]}", item['explanation'], '']
        for ev in item['evidence']:
            lines.append(f"- `{ev['source']}`: {ev['value']}")
        lines += [f"- Prosedür: `{item['policy_source']}`", '']
        if item['action']:
            lines += ['Yapılacak iş: ' + item['action'], '']
    if report['changes']:
        lines += ['## Önceki incelemeye göre değişiklikler', '']
        lines += [f"- {c['label']}: {labels[c['before']]} → {labels[c['after']]}" for c in report['changes']]
    return '\n'.join(lines)


def chat(session_id, message, selected_id=None, mode=MODE):
    """Persisted conversational UI. Intent parsing is deterministic, clearly labelled."""
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
        raise ValueError('Mesaj 1–2000 karakter olmalıdır.')
    context = storage.session(session_id)
    # Educational input heuristic; not an effective security perimeter.
    text = normalize(message)
    if any(s in text for s in ['ignore previous', 'ignore all previous', 'sistem talimat', 'tum musterileri', 'butun musterileri']):
        return {'message': 'Bu talep desteklenmiyor. Yalnızca seçili başvuru incelenebilir.',
                'guard': 'blocked', 'intent_mode': 'deterministic'}
    explicit_ids = re.findall(r'(?<!\d)\d{4}(?!\d)', message)
    if len(set(explicit_ids)) > 1:
        return {'message': 'Tek seferde bir başvuru numarası belirtin.', 'intent_mode': 'deterministic'}
    app_id = explicit_ids[0] if explicit_ids else (selected_id or context['application_id'])
    result = {'intent_mode': 'deterministic'}
    if any(word in text for word in ['prosedur', 'kural', 'kosul', 'neden']):
        hits = search_policy(message)
        result.update(message='\n\n'.join(f"{h['title']}: {h['text']}\nKaynak: {h['source']}" for h in hits)
                      if hits else 'Bu ifadeyle eşleşen prosedür maddesi bulunamadı.', sources=hits)
    elif not app_id:
        result['message'] = 'İncelenecek başvuru numarasını belirtin (1001–1005).'
    elif any(word in text for word in ['incele', 'kontrol', 'tekrar', 'yeniden', 'ekledim', 'tamamladim']):
        report = review(app_id, mode)
        result.update(report=report, message=f"{app_id} başvurusu incelendi. Açık iş sayısı: {len(report['tasks'])}. Ayrıntılar raporda.")
    else:
        report = storage.latest_report(app_id)
        if report:
            result['message'] = '\n'.join(f"• {t['label']}: {t['action']}" for t in report['tasks']) or 'Açık iş bulunmuyor; dosya uzman incelemesine hazır.'
        else:
            result['message'] = f'{app_id} için henüz inceleme yok. “Başvuruyu incele” yazabilirsiniz.'
    if app_id:
        storage.get_application(app_id)
        context['application_id'] = app_id
    context['messages'] += [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': result['message']}]
    storage.save_session(session_id, context)
    return result
