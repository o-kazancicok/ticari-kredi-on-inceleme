# Başvuru 1003 — Ön inceleme

Bu belgede, unvan uyuşmazlığı bulunan 1003 başvurusu için uygulamada ürettiğim raporu gösteriyorum. Karşılaştırılan değerleri ve prosedür referanslarını izlenebilirliği korumak için olduğu gibi bıraktım.

Dosya ön inceleme raporu • Nihai değerlendirme yetkili birim tarafından yapılır

İnceleme tarihi: 2026-10-17 | Prosedür: TIC-001 v1.0
Durum: tamamlanmasi_gereken_isler_var

## Firma unvanı — Doğrulama gerekli
Kaynaklar arasında farklı bilgi bulundu.

- `application:1003#applicant.title`: Çınar Tarım Limited Şirketi
- `customer:1003#title`: Çınar Gıda Limited Şirketi
- `document:D-1003-faaliyet_belgesi-v1#fields.title`: Çınar Tarım Limited Şirketi
- Prosedür: `policy:TIC-001@1.0#P01`

Açık iş: Firma unvanının güncel kaynak belgeyle doğrulanması.

## Vergi numarası — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.tax_id`: 0000001003
- `customer:1003#tax_id`: 0000001003
- `document:D-1003-vergi_levhasi-v1#fields.tax_id`: 0000001003
- Prosedür: `policy:TIC-001@1.0#P01`

## Hukuki şekil — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.legal_form`: LIMITED
- `customer:1003#legal_form`: LIMITED
- `document:D-1003-faaliyet_belgesi-v1#fields.legal_form`: LIMITED
- Prosedür: `policy:TIC-001@1.0#P01`

## Kuruluş tarihi — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.foundation_date`: 2020-06-15
- `customer:1003#foundation_date`: 2020-06-15
- `document:D-1003-faaliyet_belgesi-v1#fields.foundation_date`: 2020-06-15
- Prosedür: `policy:TIC-001@1.0#P01`

## Firma yaşı — Uygun
12 takvim ayı koşulu sağlandı.

- `application:1003#applicant.foundation_date`: 2020-06-15
- `review:as_of`: 2026-10-17
- Prosedür: `policy:TIC-001@1.0#P02`

## Faaliyet konusu — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.activity`: Sebze ve meyve toptan ticareti
- `customer:1003#sectors[0].value`: Sebze ve meyve toptan ticareti
- `document:D-1003-faaliyet_belgesi-v1#fields.activity`: Sebze ve meyve toptan ticareti
- Prosedür: `policy:TIC-001@1.0#P03`

## NACE kodu — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.nace`: 463101
- `customer:1003#sectors[0].code`: G.46.31.01
- `document:D-1003-faaliyet_belgesi-v1#fields.nace`: 463101
- Prosedür: `policy:TIC-001@1.0#P03`

## Zorunlu iletişim bilgileri — Uygun
Zorunlu iletişim alanları mevcut; sahiplik doğrulanmadı.

- `application:1003#applicant.address`: Merkez Mahallesi, Çınar Sokak 12, Kumluca / Antalya
- `application:1003#applicant.phone`: 0000000000
- `application:1003#applicant.email`: firma@example.invalid
- `application:1003#applicant.zip_code`: 07350
- Prosedür: `policy:TIC-001@1.0#P04`

## Adres karşılaştırması — Uygun
Kontrol edilen kaynaklardaki bilgiler eşleşiyor.

- `application:1003#applicant.address`: Merkez Mahallesi, Çınar Sokak 12, Kumluca / Antalya
- `customer:1003#address`: Merkez Mahallesi, Çınar Sokak 12, Kumluca / Antalya
- Prosedür: `policy:TIC-001@1.0#P04`

## Kefil bilgileri — Uygun
Zorunlu alanlar ve numara biçimi uygun; resmî doğrulama yapılmadı.

- `application:1003#guarantor`: {'entity_type': 'individual', 'first_name': 'Deniz', 'last_name': 'Yılmaz', 'citizen_id': '00000000001'}
- Prosedür: `policy:TIC-001@1.0#P05`

## vergi_levhasi — Uygun
Belge yaşı 16 gün; 0–90 gün koşulu sağlandı.

- `document:D-1003-vergi_levhasi-v1#issued_on`: 2026-10-01
- `document:D-1003-vergi_levhasi-v1#readable`: True
- `review:as_of`: 2026-10-17
- Prosedür: `policy:TIC-001@1.0#P07`

## faaliyet_belgesi — Uygun
Belge yaşı 16 gün; 0–90 gün koşulu sağlandı.

- `document:D-1003-faaliyet_belgesi-v1#issued_on`: 2026-10-01
- `document:D-1003-faaliyet_belgesi-v1#readable`: True
- `review:as_of`: 2026-10-17
- Prosedür: `policy:TIC-001@1.0#P07`

## mali_tablo — Uygun
Belge yaşı 16 gün; 0–90 gün koşulu sağlandı.

- `document:D-1003-mali_tablo-v1#issued_on`: 2026-10-01
- `document:D-1003-mali_tablo-v1#readable`: True
- `review:as_of`: 2026-10-17
- Prosedür: `policy:TIC-001@1.0#P07`
