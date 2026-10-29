# Yerel model yapılandırmam

İnceleme araçlarını yerel bir modelle kullanmak için Ollama ve qwen3:4b seçtim.
Native agent akışını Ollama v0.40.5 ile RTX 5080 üzerinde doğruladım.

## Kurulum akışım

Temel Python ortamından sonra model kurulumunu şu betikle yapıyorum:

```powershell
.\setup-ollama.ps1
```

Betik resmî Windows CLI paketini `runtime` klasörüne indiriyor ve yayınlanan
SHA256 özetiyle doğruluyor. Ardından `.env` içindeki modeli indiriyor.
Genel PATH değişikliği veya Windows başlangıç kaydı oluşturmuyorum.
Model ve anahtarları Ollama'nın standart kullanıcı klasörü `.ollama` altında
tutuyorum. `runtime` ve model dosyalarını Git'e veya kaynak ZIP paketine eklemiyorum.

Servis erişilebiliyorsa ikinci bir servis başlatmıyorum. Kurulu modeli tekrar
indirmiyorum. İndirme internet gerektiriyor; inceleme istekleri yerel HTTP
servisine gidiyor. Projeyle başlattığım serviste bulut özelliklerini kapatıyorum.

## Çalışma ayarlarım

```dotenv
KREDI_MODE=agent
KREDI_ENGINE=native
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
```

```powershell
.\start.ps1 -Port 8767
```

Başlatıcı, gerektiğinde Ollama'yı görünür pencere açmadan hazırlıyor. Normal
başlatmada model indirmiyorum; eksikse kurulum adımını bildiriyorum. `-Check`
yalnızca kontrol yapıyor. Servisi elle hazırlayıp kontrol etmek için kullandığım komutlar:

```powershell
.venv\Scripts\python.exe scripts/ollama_runtime.py
.venv\Scripts\python.exe app.py --check
```

Uygulamayı Ctrl+C ile kapattığımda Ollama servisini açık bırakıyorum; aynı
servisi başka yerel uygulamalar da kullanabiliyor. Ollama'nın teknik günlükleri
`runtime/ollama-server.log` dosyasında. Uygulamanın geçici işlem günlüğünü bu
hizmet günlüğünden ayrı tuttum.

Kurallı akışı açıkça seçmek için:

```powershell
.\start.ps1 -Mode demo -Port 8767
```

## Gerçek model doğrulamam

```powershell
.venv\Scripts\python.exe scripts/verify_agent.py
```

Beş başvuruyu ve eksik belge tamamlama akışını geçici bir SQLite veritabanında
gerçek modelle çalıştırdım. Bulgular aynı kontrol motorunun kurallı sonuçlarıyla
eşleşti. Normal başvuru kayıtlarını ve rapor geçmişini bu testlerde kullanmadım.
Özeti `runtime/agent-verification.json` dosyasında sakladım. Web API üzerinden
gerçek modelle incelemeyi de ayrıca doğruladım.

İlk başvuru yaklaşık 61 saniyede, sonraki başvurular yaklaşık 25–39 saniyede
tamamlandı. İlk süre model yüklemeyi de içeriyor. Bazı kaynak araçlarının tekrar
çağrıldığını gördüm. Bu ölçümleri küçük bir örnek kümesinin sonucu olarak
değerlendiriyorum; gerçek belge çeşitliliği veya kredi kararı doğruluğu için
başarı ölçümü yapmış değilim.

## Başvurduğum kaynaklar

- https://docs.ollama.com/windows
- https://ollama.com/library/qwen3:4b
- https://docs.ollama.com/capabilities/tool-calling
