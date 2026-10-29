"""Deterministic checks with field-level evidence. Never approves a credit."""
import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from .policy import POLICY, normalize, policy_source

OK = 'uygun'
MISSING = 'eksik'
VERIFY = 'dogrulama_gerekli'
UNKNOWN = 'kontrol_edilemedi'
NA = 'uygulanamaz'
GROUPS = ['identity', 'activity', 'contact', 'guarantor', 'documents']


def evidence(source, value):
    return {'source': source, 'value': value}


def finding(key, label, status, explanation, action, sources, clause):
    return {'id': key, 'label': label, 'status': status, 'explanation': explanation,
            'action': action, 'evidence': sources, 'policy_source': policy_source(clause)}


def compare(key, label, values, clause, norm=normalize):
    present = [v for v in values if v['value'] not in (None, '')]
    if len(present) != len(values):
        status, explanation, action = MISSING, 'Karşılaştırma için gerekli alan eksik.', 'Eksik alanı kaynağında tamamlayın.'
    elif len({norm(v['value']) for v in present}) > 1:
        status, explanation, action = VERIFY, 'Kaynaklar arasında farklı bilgi bulundu.', 'Güncel kaynak belgeyle bilgiyi doğrulayın.'
    else:
        status, explanation, action = OK, 'Kontrol edilen kaynaklardaki bilgiler eşleşiyor.', ''
    return finding(key, label, status, explanation, action, values, clause)


def latest_documents(docs):
    result = {}
    for doc in docs:  # chronological insertion order provided by storage
        result[doc['kind']] = doc
    return result


def doc_value(doc, field):
    if not doc.get('readable'):
        return evidence(f"document:{doc['id']}#readable", False)
    return evidence(f"document:{doc['id']}#fields.{field}", doc.get('fields', {}).get(field))


def select_sector(sectors):
    if not sectors:
        raise ValueError('Müşteri kaydında sektör bulunamadı.')
    if len(sectors) == 1:
        return sectors[0]
    priority = [s for s in sectors if str(s.get('percent', '')).strip() == '-']
    if len(priority) == 1:
        return priority[0]
    if len(priority) > 1:
        raise ValueError('Birden fazla sektörün payı -; seçim belirsiz.')
    try:
        shares = [Decimal(str(s['percent']).replace(',', '.')) for s in sectors]
    except (KeyError, InvalidOperation):
        raise ValueError('Sektör yüzdesi eksik veya geçersiz.') from None
    if any(not n.is_finite() or n < 0 or n > 100 for n in shares):
        raise ValueError('Sektör yüzdeleri 0–100 aralığında olmalıdır.')
    if sum(shares) != 100:
        raise ValueError('Çoklu sektör yüzdeleri toplamı 100 değil.')
    highest = max(shares)
    if shares.count(highest) != 1:
        raise ValueError('En yüksek sektör payı eşit; seçim belirsiz.')
    return sectors[shares.index(highest)]


def nace(value):
    return re.sub(r'[^0-9]', '', str(value or ''))


def source_values(app, customer, docs, field, doc_kind=None):
    values = [evidence(f"application:{app['id']}#applicant.{field}", app['applicant'].get(field))]
    if customer is not None:
        values.append(evidence(f"customer:{app['id']}#{field}", customer.get(field)))
    if doc_kind and doc_kind in docs:
        values.append(doc_value(docs[doc_kind], field))
    return values


def identity(app, customer, docs, as_of):
    result = []
    doc_map = latest_documents(docs)
    for field, label, kind in [('title', 'Firma unvanı', 'faaliyet_belgesi'),
                              ('tax_id', 'Vergi numarası', 'vergi_levhasi'),
                              ('legal_form', 'Hukuki şekil', 'faaliyet_belgesi'),
                              ('foundation_date', 'Kuruluş tarihi', 'faaliyet_belgesi')]:
        values = source_values(app, customer, doc_map, field, kind)
        if customer is None:
            item = finding(field, label, UNKNOWN, 'Müşteri servisi yanıt vermedi; karşılaştırma tamamlanamadı.',
                           'Servis erişimi sağlandıktan sonra yeniden inceleyin.', values, 'P01')
        elif kind not in doc_map or not doc_map[kind].get('readable'):
            item = finding(field, label, UNKNOWN, 'Karşılaştırma belgesi yok veya okunamıyor.',
                           'İlgili belgeyi tamamlayın.', values, 'P01')
        else:
            item = compare(field, label, values, 'P01')
            if field == 'tax_id' and any(not re.fullmatch(r'[0-9]{10}', str(v['value'] or '')) for v in values):
                item.update(status=MISSING if any(not v['value'] for v in values) else VERIFY,
                            explanation='Vergi numarası 10 rakam biçiminde değil.', action='Vergi numarasını doğrulayın.')
        result.append(item)
    raw = app['applicant'].get('foundation_date')
    sources = [evidence(f"application:{app['id']}#applicant.foundation_date", raw), evidence('review:as_of', as_of)]
    try:
        start, end = date.fromisoformat(raw), date.fromisoformat(as_of)
        months = POLICY['min_company_months']
        year, month = divmod(start.year * 12 + start.month - 1 + months, 12)
        anniversary = date(year, month + 1, min(start.day, calendar.monthrange(year, month + 1)[1]))
        valid = start <= end and anniversary <= end
        result.append(finding('company_age', 'Firma yaşı', OK if valid else VERIFY,
                              '12 takvim ayı koşulu sağlandı.' if valid else '12 takvim ayı koşulu sağlanmadı veya tarih gelecekte.',
                              '' if valid else 'Ürün koşulunu uzman incelemesine yönlendirin.', sources, 'P02'))
    except (ValueError, TypeError):
        result.append(finding('company_age', 'Firma yaşı', UNKNOWN, 'Kuruluş tarihi değerlendirilemedi.',
                              'Geçerli kuruluş tarihini tamamlayın.', sources, 'P02'))
    return result


def activity(app, customer, docs, as_of):
    if customer is None:
        return [finding('sector', 'Faaliyet ve NACE', UNKNOWN, 'Müşteri sektör bilgisi alınamadı.',
                        'Müşteri servisini yeniden sorgulayın.', [evidence(f"customer:{app['id']}#service", 'unavailable')], 'P03')]
    try:
        sector = select_sector(customer.get('sectors', []))
    except ValueError as exc:
        return [finding('sector', 'Faaliyet ve NACE', VERIFY, str(exc), 'Sektör seçimini uzmanla doğrulayın.',
                        [evidence(f"customer:{app['id']}#sectors", customer.get('sectors', []))], 'P03')]
    result = []
    sector_index = customer['sectors'].index(sector)
    for field, label, sector_field in [('activity', 'Faaliyet konusu', 'value'), ('nace', 'NACE kodu', 'code')]:
        values = [evidence(f"application:{app['id']}#applicant.{field}", app['applicant'].get(field)),
                  evidence(f"customer:{app['id']}#sectors[{sector_index}].{sector_field}", sector.get(sector_field))]
        activity_doc = latest_documents(docs).get('faaliyet_belgesi')
        if activity_doc and activity_doc.get('readable'):
            values.append(doc_value(activity_doc, field))
        item = compare(field, label, values, 'P03', nace if field == 'nace' else normalize)
        if field == 'nace' and any(len(nace(v['value'])) != 6 for v in values):
            item.update(status=VERIFY, explanation='NACE kodu 6 rakama dönüştürülemedi.', action='NACE kaynağını doğrulayın.')
        result.append(item)
    return result


def contact(app, customer, docs, as_of):
    values = [evidence(f"application:{app['id']}#applicant.{f}", app['applicant'].get(f))
              for f in POLICY['required_contact_fields']]
    missing = [f for f in POLICY['required_contact_fields'] if not str(app['applicant'].get(f) or '').strip()]
    result = [finding('contact_required', 'Zorunlu iletişim bilgileri', MISSING if missing else OK,
                      'Eksik alanlar: ' + ', '.join(missing) if missing else 'Zorunlu iletişim alanları mevcut; sahiplik doğrulanmadı.',
                      'Eksik iletişim alanlarını tamamlayın.' if missing else '', values, 'P04')]
    address_sources = source_values(app, customer, {}, 'address')
    result.append(compare('address', 'Adres karşılaştırması', address_sources, 'P04') if customer is not None else
                  finding('address', 'Adres karşılaştırması', UNKNOWN, 'Müşteri adresi alınamadı.',
                          'Servis erişimi sağlanınca karşılaştırın.', address_sources, 'P04'))
    return result


def guarantor(app, customer, docs, as_of):
    value = app.get('guarantor') or {}
    sources = [evidence(f"application:{app['id']}#guarantor", value)]
    if not POLICY['guarantor_required']:
        return [finding('guarantor', 'Kefil bilgileri', NA, 'Bu ürün için kefil gerekmiyor.', '', sources, 'P05')]
    if value.get('entity_type') not in ('individual', 'organization'):
        return [finding('guarantor', 'Kefil bilgileri', MISSING, 'Kefil veya kişi türü eksik/geçersiz.',
                        'Kefil kişi türünü ve bilgilerini tamamlayın.', sources, 'P05')]
    individual = value['entity_type'] == 'individual'
    required = ['first_name', 'last_name', 'citizen_id'] if individual else ['title', 'tax_id', 'tax_office']
    missing = [f for f in required if not str(value.get(f) or '').strip()]
    number = 'citizen_id' if individual else 'tax_id'
    valid = bool(re.fullmatch(r'[0-9]{11}' if individual else r'[0-9]{10}', str(value.get(number) or '')))
    status = MISSING if missing else (OK if valid else VERIFY)
    return [finding('guarantor', 'Kefil bilgileri', status,
                    'Eksik alanlar: ' + ', '.join(missing) if missing else
                    ('Zorunlu alanlar ve numara biçimi uygun; resmî doğrulama yapılmadı.' if valid else 'Kimlik/vergi numarası biçimi uygun değil.'),
                    '' if status == OK else 'Kefil bilgilerini tamamlayın veya doğrulayın.', sources, 'P05')]


def documents(app, customer, docs, as_of):
    result = []
    latest = latest_documents(docs)
    for kind in POLICY['required_documents']:
        doc = latest.get(kind)
        key = 'document_' + kind
        if doc is None:
            result.append(finding(key, kind, MISSING, 'Gerekli belge yüklenmemiş.', 'Belgeyi yükleyin.',
                                  [evidence(f"documents:{app['id']}#kinds", list(latest))], 'P06'))
            continue
        sources = [evidence(f"document:{doc['id']}#issued_on", doc.get('issued_on')),
                   evidence(f"document:{doc['id']}#readable", doc.get('readable')),
                   evidence('review:as_of', as_of)]
        if not doc.get('readable'):
            status, explanation, action = UNKNOWN, 'Belge okunamadı.', 'Metin içeren okunabilir belge yükleyin.'
        else:
            try:
                age = (date.fromisoformat(as_of) - date.fromisoformat(doc['issued_on'])).days
                valid = 0 <= age <= POLICY['max_document_days']
                status = OK if valid else VERIFY
                explanation = f'Belge yaşı {age} gün; 0–90 gün koşulu ' + ('sağlandı.' if valid else 'sağlanmadı.')
                action = '' if valid else 'Belge tarihini doğrulayın veya güncel belge yükleyin.'
            except (ValueError, TypeError, KeyError):
                status, explanation, action = VERIFY, 'Belge tarihi eksik veya geçersiz.', 'Belge tarihini doğrulayın.'
        result.append(finding(key, kind, status, explanation, action, sources, 'P07'))
    return result


CHECKERS = {name: globals()[name] for name in GROUPS}
