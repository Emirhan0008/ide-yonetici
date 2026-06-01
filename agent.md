# 🤖 Yapay Zeka & Geliştirici Bilgi Merkezi (agent.md)

Bu dosya, projeyi devralacak olan yazılımcı veya yapay zeka ajanı için kritik teknik hafızayı ve operasyonel kuralları içerir. **Lütfen geliştirmeye başlamadan önce okuyun.**

## 🎯 Proje Vizyonu ve Durumu
Bu araç, çoklu bulut IDE (Cursor, Replit vb.) kullanımından doğan "hangi proje hangi hesapta/IDE'de kaldı?" karmaşasını çözen minimalist bir yönetim panelidir. Şu an **V2.5 (Stabil)** aşamasındadır.

## 🛠️ Teknik Mimari ve Temel Prensip
- **EN BÜYÜK ÖNCELİK:** Uygulama tek bir `.pyw` dosyası çalıştırılarak (Self-contained) ayağa kalkmalıdır. Tüm HTML, CSS ve JS kodları bu dosya içinde gömülü (inline) kalmaya devam etmelidir.
- **Kütüphane Kullanımı:** Proje modern kütüphanelere (FastAPI, Flask, SQLAlchemy vb.) açıktır ancak bu paketler `requirements.txt` dosyasında listelenmelidir.
- **Frontend Gelişimi:** UI kütüphaneleri kullanılabilir, fakat nihai çıktı (bundle) Python dosyası içine gömülerek "tek dosya ile çalıştırma" özelliği korunmalıdır.

## 🛡️ Kritik Fonksiyonel Kurallar (Hata Önleyici)

### Durum Sistemi
- Durumlar: "Bitti", "Yarım Kaldı", "Bitmedi ama çalışıyor", "Pasif", "Arşiv"
- İstatistikler: "Devam Eden" = "Yarım Kaldı" + "Bitmedi ama çalışıyor" toplamı

### Taslak Sistemi (V6)
- Taslaklar `localStorage`'da `proje_taslak` anahtarıyla tutulur.
- **Debounce:** Yazım sırasında 300ms gecikme ile kaydedilir.
- **Guard:** Taslak kaydı işlemi **asla** `modalKapat` fonksiyonu içinde veya sonrasında tetiklenmemelidir.

### Modal Güvenliği
- Input alanında metin seçerken mouse dışarı kayarsa modalın kapanmaması için `mousedown` ve `click` overlay üzerinde çapraz kontrol edilir. Bu mantığı bozmayın.

### Veritabanı
- Migrasyonlar `tablolari_olustur` içinde `try-except` bloklarıyla `ALTER TABLE` şeklinde yapılmalıdır.

### Lokal Yol Temizleme
- `_lokal_yol_temizle()` fonksiyonu backend'de tırnak temizler.
- Frontend'de `f-lokal-yol` input'unda `paste` ve `input` event'leri de temizler.
- Windows "Yol olarak kopyala" özelliği `"C:\yol"` formatında verir; bu otomatik temizlenir.

### Firebase Sıkıştırma Sistemi (V2.5)
- Firebase'e gönderilen veri `zlib` (level 9) ile sıkıştırılır, `base64` ile encode edilir.
- `kart_gorseli` (Base64 görsel) Firebase'e **gönderilmez** — lokal DB'de kalır.
- Tipik tasarruf: **%60-75** (14 proje: 8.3KB → 3.1KB).
- Geri yükleme: `_veriyi_ac()` eski format (ham JSON) ile de uyumludur.
- Firebase'deki yapı: `{ meta: {...}, sikis: { v:1, z:"base64...", boyut_ham, boyut_sikis, oran } }`
- `kart_rengi`: Kullanıcı seçimi. Boş ise durum rengine göre otomatik.
- `kart_gorseli`: Base64 encoded görsel. DB'de TEXT olarak saklanır. Max 2MB.
- Görsel kart arka planında `blur(8px) opacity(0.18)` ile gösterilir.
- Uygulama arka planı `localStorage`'da `app_bg_image` anahtarıyla saklanır.

### Hızlı IDE/Hesap Ekleme (V2.5)
- Form içindeki "+" butonları `hizli-ide-panel` / `hizli-hesap-panel` div'lerini açar.
- Paneller birbirini kapatır (aynı anda ikisi açık olamaz).
- `hizliIdeKapat()` ve `hizliHesapKapat()` `modalAc()` içinde çağrılır.

## 📂 Önemli Dosyalar ve Konumlar
- `ide_yonetici.pyw`: Tüm uygulama (Backend + Frontend) buradadır.
- `ide_yonetici.db`: SQLite veritabanı (script ile aynı dizinde).
- `firebase_ayarlar.json`: Firebase/Google yapılandırması — `.gitignore`'da, commit etme!
- `dist/IDE_Yonetici.exe`: PyInstaller ile üretilen taşınabilir sürüm.

## �️ Veritabanı Şeması (projeler tablosu)
```
id, proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email,
durum, notlar, son_guncelleme, olusturma_tarihi, etiketler,
lokal_yol, deploy_url, kart_rengi, kart_gorseli
```

## �🚀 İş Akışı ve Doğrulama
1. **Geliştirme:** `ARAYUZ_HTML` değişkeni içindeki JS/CSS kodlarını güncelleyin.
2. **Yenileme:** Değişikliklerin yansıması için Python sürecini durdurup (`Ctrl+C`) tekrar başlatın. Tarayıcıda `Ctrl+F5` yapın.
3. **Tanılama:** `/api/diagnostic` uç noktasının "Healthy" döndüğünü doğrulayın.

## ⚠️ Bilinen "Gotcha"lar
- **Port Çakışması:** Sunucu `8888` meşgulse otomatik olarak portu artırır.
- **Büyük Görseller:** `kart_gorseli` Base64 olarak DB'de saklanır. 500KB görsel ~670KB yer kaplar. Çok sayıda büyük görselli proje DB boyutunu artırır.
- **Tarayıcı Kapanınca:** `beforeunload` event'i `navigator.sendBeacon('/api/kapat')` çağırır, Python süreci kapanır.
- **`firebase_ayarlar.json`:** Gerçek API key içerir, asla commit etme.
