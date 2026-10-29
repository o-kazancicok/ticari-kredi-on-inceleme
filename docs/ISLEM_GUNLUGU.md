# İşlem günlüğü tasarımım

Uygulamada her adımı loglamak yerine kritik işlemlerin öncesini ve sonucunu
izleyecek bir günlük oluşturdum. Kayıtları doğrudan uygulamanın çalıştığı
PowerShell terminaline yazıyorum; İşlem günlüğü sekmesinde de iki saniyede bir
yenileyerek gösteriyorum. İnceleme devam ederken bu sekme açılabiliyor.

## İzlediğim işlemler

- Başvuru incelemesi.
- Müşteri kaydı sorgusu.
- Yerel model çağrısı.
- Belge yükleme, kaydetme ve silme.
- Rapor kaydetme ve dışa aktarma.
- Uygulama oturumu ve sunucu hata bildirimleri.

Rutin sayfa açma ve listelemeleri ayrıca loglamıyorum. Günlüğün okunması da yeni
kayıt oluşturmuyor. Böylece takip etmek istediğim adımların gereksiz kayıtlar
arasında kaybolmasını önlemeyi hedefledim.

## Kayıt yapım

Kritik işlem başlamadan `started`, tamamlandığında `completed`, hata aldığında
`failed` kaydı oluşturuyorum. Müşteri servisine erişilemediğinde sorguyu
`unavailable` sonucuyla ve uyarı seviyesinde kaydediyorum.

Aynı incelemenin alt adımlarını `trace_id` ile birleştirdim. İşlem ve üst işlem
kimlikleri sayesinde model çağrısını, müşteri sorgusunu ve rapor kaydını
ilişkilendirebiliyorum. Başvuru numarası, süre, hata türü ve kontrol/araç çağrısı
sayısı gibi sınırlı bilgileri kullanıyorum.

Belge içeriğini ve dosya adını, sohbet metnini, model istemini/yanıtını, müşteri
adını, kimlik/vergi numarasını veya anahtarları günlüğe yazmıyorum. Zamanları
UTC olarak tutuyor, terminalde ve ekranda İstanbul saatiyle gösteriyorum.

## Oturum ve saklama kararım

Uygulamanın günlük kopyasını dosyaya veya SQLite'a yazmıyorum. En fazla 2.000
kaydı bellekte tutuyorum; sınır dolduğunda en eski kayıtları çıkarıyorum.
Arayüzde son 100 kaydı gösteriyorum.

Python uygulaması Ctrl+C ile kapandığında bu kopyayı temizliyorum. Süreç zorla
sonlandırıldığında da bellekteki kayıtlar kayboluyor. Yeni oturumda önceki
kayıtları yüklemiyorum. Önceki sürümden kalan uygulama günlük dosyalarını da
başlangıçta temizliyorum; kilitli dosya varsa uyarı oluşturuyorum.

Tarayıcı sekmesini kapatmak çalışan Python sürecini durdurmuyor. Terminalde
yazdırılmış satırların ekran geçmişini ise terminalin kendisi yönetiyor;
uygulamadan PowerShell geçmişini temizlemiyorum. Bu yapıyı geçici operasyon
takibi için kullandım, kalıcı bir denetim kaydı olarak tasarlamadım.

Ollama ayrı bir hizmet olarak çalışıyor. Uygulamanın bu günlük davranışını
Ollama'nın kendi teknik hizmet günlüğünden ayrı tuttum.

## Yerel API

Günlüğü `GET /api/logs` üzerinden de erişilebilir yaptım. `records` kayıtları,
`session_id` uygulama oturumunu, `capacity` bellek sınırını içeriyor. Yanıt
önbelleğe alınmıyor ve yerel erişim kontrolleri bu uçta da geçerli.
Model çağrısı sürerken kayıtlar okunabiliyor.

İşlem öncesi yazmayı, hata kaydını, eşzamanlı başvuruların takip kimliklerini,
içeriklerin loga taşınmamasını, bellek sınırını, kapanışta temizlemeyi ve terminal
çıktısını otomatik testlerle doğruladım.
