# 🤖 Yapay Zeka & Geliştirici Bilgi Merkezi (agent.md)

Bu dosya, projeyi devralacak olan yazılımcı veya yapay zeka ajanı için kritik teknik hafızayı ve operasyonel kuralları içerir. **Lütfen geliştirmeye başlamadan önce okuyun.**

## 🎯 Proje Vizyonu ve Durumu
Bu araç, çoklu bulut IDE (Cursor, Replit vb.) kullanımından doğan "hangi proje hangi hesapta/IDE'de kaldı?" karmaşasını çözen minimalist bir yönetim panelidir. Şu an **V2.5 (Stabil)** aşamasındadır.

## 🛠️ Teknik Mimari ve Temel Prensip
- **CANLI KAYNAK:** `public/index.html` Firebase Hosting üzerinden yayınlanır (`https://ideyonetici.web.app`). Tek geliştirme hedefi budur.
- **ARŞİV:** Masaüstü `ide_yonetici.pyw` uygulaması `docs/archive/` altına taşındı; `cloudrun/` kaldırıldı. Lokal SQLite/HTTP backend artık kullanılmıyor.
- **Kütüphane Kullanımı:** Frontend UI kütüphaneleri CDN üzerinden yüklenebilir (örn. Firebase SDK).

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

### Kimlik Doğrulama (V2.5 Hosting)
- `public/index.html` shim'i Firebase Auth (Google Sign-In popup) kullanır.
- Kullanıcının `uid`'si Realtime Database'de `users/$uid` path'inde izole edilir (bkz. `database.rules.json`).
- `firebase_ayarlar.json` **artık kullanılmıyor** (legacy dosya, shim hardcode edilmiş). İleride runtime config gerekirse shim'e taşınmalı.

## 📂 Önemli Dosyalar ve Konumlar
- `public/index.html`: Firebase Hosting frontend'i (tek canlı kaynak: shim + UI).
- `docs/archive/ide_yonetici.pyw`: Arşivlenen masaüstü uygulaması (artık çalıştırılmaz, referans için saklanır).
- `docs/archive/`: Eski PRD'ler ve uygulanmamış planlar.

## 🗄️ Veritabanı Şeması (projeler tablosu)
```
id, proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email,
durum, notlar, son_guncelleme, olusturma_tarihi, etiketler,
lokal_yol, deploy_url, kart_rengi, kart_gorseli
```

## 🚀 İş Akışı ve Doğrulama
1. **Geliştirme:** `public/index.html` içindeki JS/CSS kodlarını güncelleyin.
2. **Yenileme:** Tarayıcıda `Ctrl+F5` yapın.
3. **Deploy:** Frontend değişikliklerini `firebase deploy --only hosting` ile yayınlayın.

## ⚠️ Bilinen "Gotcha"lar
- **Tarayıcı Cache:** Hosting header'ları `no-store` zorlar; yine de testte `Ctrl+F5` yapın.
