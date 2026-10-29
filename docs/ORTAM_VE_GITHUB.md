# Ortam ve GitHub yapılandırmam

## Windows kurulumu

Projeyi Python 3.11 ve üzeriyle çalışacak şekilde hazırladım. Temel kurulum akışı:

```powershell
.\setup.ps1
.\start.ps1 -Port 8767
```

Python PATH üzerinde bulunmuyorsa kurulum betiği açık bir yol kabul ediyor:

```powershell
.\setup.ps1 -PythonPath 'C:\Python312\python.exe'
```

Bağımlılıkları `.venv` altında tutuyorum. Kurulumda `requirements-lock.txt`
sürümlerini kullanıyor, mevcut `.env` ve başvuru kayıtlarını koruyorum.
Sanal ortamı elle etkinleştirmeye ihtiyaç bırakmadım.

Başlatıcı HTTP yanıtını doğruladıktan sonra **http://localhost:8767** adresini
tarayıcıda açıyor. `-NoBrowser` ile otomatik açmayı kapatabiliyor, Ctrl+C ile
uygulamayı durdurabiliyorum. `start-demo.ps1` dosyasını kurallı modu açıkça seçen
başlatıcı olarak korudum.

## Ortam ayarlarım

| Değişken | Varsayılan | Kullanım |
|---|---|---|
| KREDI_MODE | demo | Kurallı akış veya agent |
| KREDI_ENGINE | native | Native döngü veya isteğe bağlı langgraph |
| KREDI_PORT | 8765 | Yerel uygulama portu; komut satırından 8767 seçebiliyorum |
| KREDI_DATA_DIR | proje/runtime | SQLite ve belge kayıtlarının veri dizini |
| OLLAMA_URL | http://127.0.0.1:11434 | Yerel Ollama servisi |
| OLLAMA_MODEL | qwen3:4b | Yerel model adı |

Ayar önceliğini komut satırı > terminal/CI ortamı > `.env` > varsayılanlar
olarak belirledim. `.env` proje kökünden UTF-8 okunuyor; değerlerde değişken
genişletmesi yapmıyorum. Paylaşım için `.env.example` şablonunu kullanıyorum.
Yerel çalışma kopyam agent modunda; şablon kurallı modla başlıyor.

`-Check` ile Python sürümünü, ayarları, bağımlılıkları ve veri dizinine yazmayı
kontrol ediyorum. Agent modunda Ollama erişimi ve kurulu model de kontrol ediliyor.
Bu komut sunucu başlatmıyor, başvuru veya rapor oluşturmuyor.
Ollama'nın hazır olmadığı durumda önce `scripts/ollama_runtime.py` çalışıyor.

## Yerel model ve isteğe bağlı motorlar

Native koordinatörü temel Python ortamı ve yerel Ollama ile çalıştırıyorum.
Model kurulumu için `.\setup-ollama.ps1` hazırladım.
LangGraph/FastMCP bağımlılıklarını temel kilit dosyasından ayrı tutuyorum:

```powershell
.\setup.ps1 -Agent
```

LangGraph seçimi `KREDI_ENGINE=langgraph` ile yapılıyor. Native akışı gerçek
modelle doğruladım; LangGraph ve MCP entegrasyonlarını henüz doğrulamadım.

## Kontroller ve bağımlılık sürümleri

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts/verify_http.py
```

HTTP doğrulamasında Node.js 22+ kullanıyorum. Betik geçici bir veri dizini ve
boş port seçiyor; sunucuyu kendisi başlatıp kapatıyor. Normal kayıtları kullanmıyor.
Otomatik birim testlerini, yerel uygulama agent modundayken de kurallı çalışacak
şekilde ayırdım. Gerçek model testini `scripts/verify_agent.py` ile yürütüyorum.

Temel uygulama ve test bağımlılıklarını `requirements-lock.txt` içinde sabitledim.
Sürüm güncellemesinde temiz ortamda `requirements-dev.txt` kurulumu ve testlerden
sonra `python -m pip freeze` çıktısını alıyorum. Agent bağımlılıklarını temel
kilit dosyasına karıştırmıyorum.

## Günlükler

Kritik adımları terminale yazıyor, İşlem günlüğü sekmesinde de gösteriyorum.
Uygulamanın günlük kopyasını yalnızca bellekte tutuyor ve süreç kapanınca siliyorum.
Terminal ekran geçmişini terminalin kendisi yönetiyor.
[İşlem günlüğü ayrıntıları](ISLEM_GUNLUGU.md).

## Kaynak depo ve CI

Kaynak kodu ve kurgusal çalışma görsellerini
[o-kazancicok/ticari-kredi-on-inceleme](https://github.com/o-kazancicok/ticari-kredi-on-inceleme)
deposunda paylaşıyorum. `.env`, sanal ortam, `runtime`, SQLite dosyaları, günlükler
ve IDE ayarları Git dışında; `.env.example` paylaşımda yer alıyor.

GitHub Actions, Windows/Ubuntu ve Python 3.11/3.12 için bağımlılık, ortam,
birim/PDF ve HTTP kontrollerini çalıştırır. Gerçek müşteri verisi, model veya
API anahtarı gerektirmez. Çalışma sonuçları deponun Actions sekmesinde izlenebilir.
