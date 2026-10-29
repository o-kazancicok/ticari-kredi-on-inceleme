# Başvuru inceleme sunum akışım

## Kurallı akış

İlk bölümde modelden bağımsız kontrol motorunu ve dosya takibini gösteriyorum.
Uygulamayı bu bölüm için aşağıdaki komutla başlatıyorum:

```powershell
.\start.ps1 -Mode demo -Port 8767
```

1. **1002 — Eksik mali tablo** başvurusunu inceliyorum. On üç kontrol içinden
   birinin eksik çıktığını, karşılaştırılan belge listesini ve P06 dayanağını gösteriyorum.
2. **Belgeler → Mali tabloyu ekle** adımından sonra sohbete **Tekrar incele** yazıyorum.
   Açık iş sayısı birden sıfıra iniyor; önceki rapor korunuyor ve değişen kontrol görünüyor.
3. **1003** başvurusunu inceliyorum. Unvan farkında sistem bir kaynağı kendiliğinden
   doğru kabul etmiyor; farklı değerleri gösterip doğrulama işi oluşturuyor.
4. **1005** başvurusunda müşteri servisinden veri alınamadığı durumu gösteriyorum.
   Altı kontrol **Kontrol edilemedi** sonucunda kalıyor; dosya hazır sayılmıyor.
5. Sohbete **Belge tarihi kuralı nedir?** yazarak ilgili prosedür maddesini görüntülüyorum.
6. Raporu Markdown olarak indirip bulguların kaynak ve dayanak bağlantılarını inceliyorum.

Bu akışta 1002 başvurusunun başlangıçta mali tablosunun eksik olması gerekiyor.
Belgeyi daha önce tamamladıysam sunumu ayrı bir `KREDI_DATA_DIR` ile hazırlıyorum;
normal kayıt geçmişini silmiyorum.

## Yerel model akışı

İkinci bölümde native agent koordinatörünü Ollama ve qwen3:4b ile çalıştırıyorum:

```powershell
.\start.ps1 -Mode agent -Port 8767
```

**İşlem akışı** sekmesinde modelin seçtiği araçları, terminalde ve **İşlem günlüğü**
sekmesinde ise kritik adımların başlangıç ve sonuçlarını takip ediyorum.
Nihai kontrol sonuçlarının aynı kod motorundan geldiğini açıklıyorum.

Gerçek modelle beş başvuruyu, belge tamamlama sonrası incelemeyi ve web API
incelemesini doğruladım. Bu testleri gerçek banka verisinde LLM başarı oranı
olarak değerlendirmiyorum. Kurallı moddaki senaryo eşleşmesini de modelin
bağımsız muhakeme başarısından ayrı tutuyorum.

## Proje özetim

Ticari kredi dosyalarının ön hazırlığında farklı kaynaklardan gelen firma ve belge
bilgilerini karşılaştıran, eksikleri dayanaklarıyla raporlayan ve belge
tamamlandığında incelemeyi sürdüren bir uygulama geliştirdim. Sabit iş kurallarını
kodla, araç seçimini yerel modelle ele aldım. Kurallı akışı agent yaklaşımı için
karşılaştırma tabanı olarak kullanıyorum. Banka çalışanının incelemeye hazırlık
yükünü azaltmayı hedefliyorum; gerçek bankadaki zaman tasarrufunu henüz ölçmedim.
