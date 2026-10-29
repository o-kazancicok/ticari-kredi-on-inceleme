"""Five entirely fabricated applications. Source documents are structured demo records."""
import copy
from . import storage


def base_application(number):
    company = {
        'title': {1001: 'Güney Tarım Limited Şirketi', 1002: 'Akdeniz Gıda Limited Şirketi',
                  1003: 'Çınar Tarım Limited Şirketi', 1004: 'Bereket Gıda Limited Şirketi',
                  1005: 'Maviova Tarım Limited Şirketi'}[number], 'tax_id': f'{number:010d}',
        'legal_form': 'LIMITED', 'foundation_date': '2020-06-15',
        'activity': 'Sebze ve meyve toptan ticareti', 'nace': '463101',
        'address': 'Merkez Mahallesi, Çınar Sokak 12, Kumluca / Antalya',
        'phone': '0000000000', 'email': 'firma@example.invalid', 'zip_code': '07350',
    }
    return {'id': str(number), 'product': 'TIC-001', 'scenario': '',
            'applicant': company, 'customer': copy.deepcopy(company) | {
                'sectors': [{'code': 'G.46.31.01', 'value': company['activity'], 'percent': '100'}]},
            'customer_service_error': False,
            'guarantor': {'entity_type': 'individual', 'first_name': 'Deniz', 'last_name': 'Yılmaz',
                          'citizen_id': '00000000001'}}


def document(application, kind, suffix='v1'):
    return {'id': f"D-{application['id']}-{kind}-{suffix}", 'kind': kind,
            'name': f"{application['id']}_{kind}_{suffix}.txt", 'issued_on': '2026-10-01',
            'readable': True, 'synthetic': True,
            'fields': {key: application['applicant'][key] for key in
                       ['title', 'tax_id', 'legal_form', 'foundation_date', 'activity', 'nace']},
            'text': 'Firma bilgileri ve faaliyet kaydı.'}


def seed():
    storage.init_db()
    if storage.list_applications():
        return
    names = {1001: 'İncelemeye hazır', 1002: 'Belge bekleniyor', 1003: 'Bilgi doğrulaması',
             1004: 'Kefil bilgileri', 1005: 'Kayıt sorgulaması'}
    for number, scenario in names.items():
        app = base_application(number)
        app['scenario'] = scenario
        if number == 1003:
            app['customer']['title'] = 'Çınar Gıda Limited Şirketi'
        if number == 1004:
            app['guarantor']['citizen_id'] = ''
        if number == 1005:
            app['customer_service_error'] = True
        with storage.connect() as db:
            db.execute('INSERT INTO applications VALUES(?,?)', (app['id'], storage.dump(app)))
        for kind in ['vergi_levhasi', 'faaliyet_belgesi', 'mali_tablo']:
            if number == 1002 and kind == 'mali_tablo':
                continue
            storage.add_document(app['id'], document(app, kind))
