"""Versioned fictional product policy; controls use structured rules, not LLM guesses."""
import re
import unicodedata

POLICY = {
    'id': 'TIC-001', 'version': '1.0', 'effective_from': '2026-10-01',
    'product': 'İşletme Kredisi', 'fictional': True,
    'min_company_months': 12, 'max_document_days': 90,
    'required_documents': ['vergi_levhasi', 'faaliyet_belgesi', 'mali_tablo'],
    'required_contact_fields': ['address', 'phone', 'email', 'zip_code'],
    'guarantor_required': True,
    'clauses': [
        {'id': 'P01', 'title': 'Firma kimliği', 'text': 'Başvuru, müşteri kaydı ve belgelerde firma unvanı, vergi numarası, hukuki şekil ve kuruluş tarihi karşılaştırılır. Kaynak farkları otomatik düzeltilmez; doğrulamaya yönlendirilir.'},
        {'id': 'P02', 'title': 'Firma yaşı', 'text': 'Ürün kapsamında kuruluş üzerinden en az 12 takvim ayı geçmesi aranır. Koşul sağlanmazsa uzman doğrulaması istenir; kredi kararı verilmez.'},
        {'id': 'P03', 'title': 'Faaliyet ve NACE', 'text': 'Tek sektör varsa o seçilir. Birden çok sektörde payı - olan kayıt önceliklidir; aksi hâlde en yüksek pay seçilir. Birden çok öncelikli kayıt veya eşit en yüksek pay belirsizdir. Faaliyet açıklaması value alanından alınır. NACE kodu harf ve noktalardan arındırılarak 6 rakam olarak karşılaştırılır.'},
        {'id': 'P04', 'title': 'İletişim', 'text': 'Adres, telefon, e-posta ve posta kodu mevcut olmalıdır. Başvuru adresi müşteri kaydıyla karşılaştırılır. Kaynak önceliği müşteri kaydında çözümlenmiş kabul edilir; telefon veya e-posta sahipliği doğrulanmaz.'},
        {'id': 'P05', 'title': 'Kefil', 'text': 'Bu ürün kapsamında kefil zorunludur. Gerçek kişide ad, soyad ve 11 rakamlı kimlik alanı; tüzel kişide unvan, 10 rakamlı vergi numarası ve vergi dairesi aranır. Numara kontrolleri yalnızca biçim kontrolüdür; resmî kimlik doğrulaması değildir.'},
        {'id': 'P06', 'title': 'Belgeler', 'text': 'Vergi levhası, faaliyet belgesi ve mali tablo bulunmalıdır. Aynı türde en son eklenen belge incelemeye alınır. Mali tablonun finansal yeterliliği veya kredi riski değerlendirilmez.'},
        {'id': 'P07', 'title': 'Belge tarihi ve erişim', 'text': 'Her belge için düzenleme tarihi ile inceleme tarihi arasında en fazla 90 gün aranır. Gelecek tarih ve geçersiz tarih doğrulamaya gider. Okunamayan belgeden olumlu sonuç çıkarılmaz. Belge güncelliği ürün prosedürüne göre değerlendirilir.'},
        {'id': 'P08', 'title': 'Sonuç ve yetki', 'text': 'Eksik veya belirsiz bilgi açıkça raporlanır. Müşteri servisi hatası kontrol edilemedi olarak gösterilir. Nihai kredi kararı, kredi skoru veya onay önerisi üretilmez. Her bulgu kaynak referansı taşır.'},
    ],
}


def normalize(text):
    text = str(text or '').translate(str.maketrans('ıİşŞğĞüÜöÖçÇ', 'iissgguuoocc')).lower()
    return re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', text)).strip()


def search_policy(query, limit=3):
    """Local lexical retrieval baseline, explicitly not embedding / semantic RAG."""
    terms = set(normalize(query).split())
    hits = []
    for clause in POLICY['clauses']:
        tokens = set(normalize(clause['title'] + ' ' + clause['text']).split())
        score = len(terms & tokens)
        if score:
            hits.append(clause | {'score': score, 'source': f"policy:{POLICY['id']}@{POLICY['version']}#{clause['id']}"})
    return sorted(hits, key=lambda item: -item['score'])[:limit]


def policy_source(clause):
    return f"policy:{POLICY['id']}@{POLICY['version']}#{clause}"
