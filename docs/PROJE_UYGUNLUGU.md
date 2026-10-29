# Bootcamp final projesi kapsamı

Ticari kredi dosyalarının ön hazırlığını, kurgusal verilerle çalışan yerel bir
agent uygulaması olarak geliştirdim. Projenin teslim kapsamını aşağıda özetledim.

| Değerlendirme alanı | Projedeki karşılığı |
|---|---|
| Problem ve gerçek dünya uyumu | Başvuru, müşteri kaydı ve belgeler arasındaki eksik ve tutarsızlıkların tespiti |
| Agentic mimari | Yerel LLM, izinli araç çağrıları, çok turlu koordinasyon ve kalıcı başvuru bağlamı |
| İşlevsellik | Beş senaryo, belge ekleme/silme, yeniden inceleme, rapor geçmişi ve servis hatası yönetimi |
| Teknik uygulama | Modüler Python katmanları, SQLite, ortam şablonu ve otomatik testler |
| Dokümantasyon | Kurulum, kullanım, mimari, doğrulama kayıtları ve yedi çalışma görseli |

Model araçları seçiyor, araç sonuçlarını sonraki turlarda kullanıyor. İş kuralları
ve nihai bulgular deterministik kontrol motorundan geliyor. Model hatasında
kurallı moda sessiz geçiş yapılmıyor. Kurallı modu karşılaştırma tabanı olarak kullanıyorum.

Doğrulanmış ana motor native. LangGraph ve FastMCP isteğe bağlı adaptörler;
entegrasyonları doğrulanmış özellikler arasında değil. Prosedür araması anahtar
kelime tabanlı; anlamsal RAG veya çoklu agent kullanmıyorum.

Kaynak kod, kurulum komutları ve görseller bu depoda; test ayrıntıları
[doğrulama kaydında](DOGRULAMA.md), çalışma görselleri
[galeride](ekran-goruntuleri/README.md) yer alıyor. Bu kapsam eğitim projesine ait;
gerçek bankada performans veya üretim uygunluğu iddiası taşımıyor.
