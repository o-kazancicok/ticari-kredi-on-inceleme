# Doğrulama kayıtlarım — 29 Ekim 2026

Bu belgede mevcut sürümde tamamladığım kontrolleri ve henüz doğrulamadığım
başlıkları bir araya getirdim. Otomatik testleri normal başvuru veritabanından
ayrı, geçici SQLite dosyalarında çalıştırdım.

| Kontrol | Elde ettiğim sonuç |
|---|---|
| Python 3.12.14 ile otomatik test paketi | 41 test geçti |
| Metin PDF okuma ve metinsiz PDF'yi okunamaz sayma | PDF testleri geçti; toplam test sayısına dahil |
| Beş kurgusal senaryoda beklenen açık bulgular | 5/5 eşleşti |
| İzole veritabanıyla temel HTTP akışı | 22 HTTP isteği geçti |
| Localhost erişimi | Doğrulandı |
| Temiz kaynak kopyası ve yeni sanal ortam | Aynı Windows bilgisayarında setup.ps1 ile bağımlılıklar yeniden kuruldu; 41 test ve 22 HTTP kontrolü geçti |
| 1002: mali tablo ekleme ve yeniden inceleme | Açık iş 1 → 0; önceki rapor korundu |
| JavaScript sözdizimi | `node --check static/app.js` geçti |
| Agent araç ön koşul hatasından toparlanma | Kontrollü model yanıtlarıyla doğrulandı |
| Bitmeyen model yanıtı | Adım sınırında durduruldu |
| Gerçek Ollama / qwen3:4b / native agent | Beş başvuru ve belge tamamlama sonrası inceleme geçti |
| Gerçek modelle web API incelemesi | 1001 başvurusunda 13 uygun kontrol, açık iş yok |
| Kritik işlem günlüğü | İşlem öncesi kayıt, hata kaydı ve ortak takip kimliği doğrulandı |
| Günlüklerde eşzamanlı başvurular | Başvuruların takip kimlikleri karışmadı |
| Günlüklerde veri sınırı | Belge, sohbet, model içeriği ve dosya adı kaydedilmedi |
| Geçici günlük ve terminal çıktısı | Bellek sınırı, kapanışta temizleme ve terminale yazma doğrulandı |
| LangGraph motoru | Henüz doğrulamadım |
| FastMCP istemci bağlantısı | Henüz doğrulamadım |
| Gerçek banka servisleri | Bağlamadım |
| Bankada süre / maliyet tasarrufu | Henüz ölçmedim |

HTTP kontrollerinde başlangıç verisini, statik sayfa ve JavaScript erişimini,
incelemeyi, belge eklemeyi, sohbetle yeniden incelemeyi, rapor dışa aktarmayı,
olay geçmişini, servis hatasını, bilinmeyen başvuruyu, farklı Origin reddini ve
geçersiz dosya türü reddini sınadım. Buna ek olarak günlük API'sinin kendisini
loglamadığını ve uygulamanın günlük dosyası oluşturmadığını kontrol ettim.

## Gerçek model ölçümlerim

Ollama **v0.40.5**, model **qwen3:4b**, koordinatör **native**, donanım **RTX 5080**.
Model 16.384 token bağlamla GPU üzerinde çalıştı.

| Başvuru | Sonuç | Süre | Araç çağrısı |
|---|---|---|---|
| 1001 | 13 uygun | 60,70 sn | 13 |
| 1002 | 12 uygun, 1 eksik | 25,49 sn | 14 |
| 1003 | 12 uygun, 1 doğrulama gerekli | 33,45 sn | 13 |
| 1004 | 12 uygun, 1 eksik | 28,42 sn | 13 |
| 1005 | 6 uygun, 6 kontrol edilemedi | 38,51 sn | 9 |

İlk başvurunun süresine model yükleme dahil. Bunlar küçük test kümesindeki tek
çalıştırmanın sonuçları; genel performans ölçümü olarak değerlendirmiyorum.
Modelin bazı kaynak araçlarını tekrar çağırdığını gözlemledim.

1002 başvurusuna mali tablo eklendikten sonra gerçek modelle yeniden inceleme
13 uygun kontrolle tamamlandı. Ayrı web API incelemesinde 1001 başvurusu
60,67 saniyede tamamlandı. Ölçüm özetlerini `runtime/agent-verification.json`
ve `runtime/agent-http-verification.json` dosyalarında yerel olarak sakladım;
Git kapsamına dahil değiller.

Sonuçları aynı kontrol motorunun kurallı çıktılarıyla karşılaştırdım. Böylece
modelin araçları kullanarak incelemeyi tamamladığını doğruladım. Gerçek belge
çeşitliliğini, ek kaynak araştırmasının kalitesini ve banka iş sonuçlarını bu
testlerle ölçmüş değilim.

## Model kullanım ölçümleri

17 Ekim 2026 tarihinde model kullanım ekranını ekledikten sonra 37 otomatik test,
12 temel HTTP kontrolü ve arayüzün sayaç gösterimi kontrolleri geçti. Çok turlu
toplamı, eksik ölçümleri, eski rapor gösterimini ve kurallı modu ayrıca doğruladım.

Ayrı geçici veri kümesinde 1001 başvurusunu gerçek qwen3:4b modeli ve native
motorla inceledim. 13 kontrol uygun çıktı. Üç model çağrısında 17.080 giriş,
4.703 çıkış, toplam 21.783 token ölçüldü. İnceleme yaklaşık 27,94 saniye,
model süresi 27,88 saniye ve çıkış üretim hızı 185,4 token/sn oldu.
Sayaçların raporla birlikte kaydedilip geri okunmasını doğruladım.
Bunlar tek bir yerel koşunun sonuçları; genel performans taahhüdü değil.


## Belge silme akışı

29 Ekim 2026 tarihinde belge silmeyi ekledikten sonra 41 otomatik test ve
22 HTTP isteğiyle temel akışları doğruladım. Başka başvurunun belgesinin
silinememesini, tekrarlanan ve geçersiz silme isteklerini, geçmiş kaydı
başarısızsa silmenin geri alınmasını ve uygulama yeniden açıldığında silinen
belgenin geri gelmemesini kontrol ettim. Yanlış eklenen son belge silindiğinde
önceki belgenin tekrar kullanılmasını ve eski raporun korunup güncellik uyarısı
almasını da doğruladım. Bu testlerde kurgusal ve geçici veri kümeleri kullandım.
