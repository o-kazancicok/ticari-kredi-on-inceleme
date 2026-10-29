# Projenin iş değeri

## Hedeflediğim iş

Bu projede ticari kredi dosyasının uzman incelemesine hazırlanmasını ele aldım.
Başvuru beyanını, müşteri kaydını ve belgeleri karşılaştırıyor; eksik ve tutarsız
bilgileri kaynaklarıyla birlikte takip ediyorum. İlk sürümü tek ürün ve tüzel firma
kapsamında geliştirdim. Kredi kararı, risk skoru, limit tahsisi ve finansal
yeterlilik değerlendirmesini kapsam dışında bıraktım.

## İş değeri ve ölçüm sınırı

| Beklentim | Ölçüm | Planladığım değerlendirme |
|---|---|---|
| Dosya hazırlama süresini azaltmak | Dosya başına aktif çalışan dakikası | Benzer zorlukta dosyalarda araçlı ve araçsız incelemeyi karşılaştırmak |
| Eksikleri daha erken bulmak | Uzmanın doğruladığı eksiklerde recall | Bağımsız uzman kontrol listesini referans almak |
| Gereksiz uyarıları sınırlamak | Precision ve dosya başına yanlış uyarı | Yanlış uyarıları nedenlerine göre sınıflandırmak |
| Dosyanın eksik nedeniyle geri dönmesini azaltmak | Geri dönen dosya oranı | Benzer ürün ve firma segmentlerini karşılaştırmak |
| Bulguların değerlendirilmesini kolaylaştırmak | Kaynağa erişim süresi ve doğru kaynak oranı | Kaynak bulunmasını ve kaynak doğruluğunu ayrı ölçmek |

Gerçek bankada süre, maliyet veya başarı oranı ölçümü yapmadım. Kurgusal başvuru
testlerini bu katkıların kanıtı olarak kullanmıyorum; bu testlerle öncelikle
inceleme akışının tutarlılığını doğruladım.

## Agent için yaptığım ayrım

Vergi numarası eşleşmesi ve zorunlu belge listesi gibi sabit kontrolleri kodla
uyguladım. Yerel modele araç seçimini ve kaynaklar arasında araştırmayı yönlendirme
rolünü verdim. İki modda aynı kontrol motorunu kullanarak modelin ek süre ve
maliyetine karşı sağlayabileceği faydayı ayrı ölçebileceğim bir yapı kurdum.

Native agent akışını gerçek Ollama modeliyle beş başvuruda ve belge tamamlama
senaryosunda doğruladım. Bu sonuç, modelin araçları kullanarak kontrolleri
tamamlayabildiğini gösteriyor. Belirsiz bulgularda ek araştırmanın kalitesini ve
gerçek belge çeşitliliğindeki katkısını henüz ölçmedim.

Belge alanlarını etiketli metinden okuyorum. Prosedür aramasında anahtar kelime
eşleşmesi kullanıyorum; serbest biçimli belge yorumlama veya anlamsal RAG eklemedim.
Modelin serbest metnini bir kredi değerlendirmesi olarak kullanmıyorum.
