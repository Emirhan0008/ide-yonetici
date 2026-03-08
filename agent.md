# 🤖 Yapay Zeka & Geliştirici Bilgi Merkezi (agent.md)

Bu dosya, projeyi devralacak olan yazılımcı veya yapay zeka ajanı için kritik teknik hafızayı ve operasyonel kuralları içerir. **Lütfen geliştirmeye başlamadan önce okuyun.**

## 🎯 Proje Vizyonu ve Durumu
Bu araç, çoklu bulut IDE (Cursor, Replit vb.) kullanımından doğan "hangi proje hangi hesapta/IDE'de kaldı?" karmaşasını çözen minimalist bir yönetim panelidir. Şu an **V2.0 (Stabil)** aşamasındadır.

## 🛠️ Teknik Mimari ve Temel Prensip
- **EN BÜYÜK ÖNCELİK:** Uygulama tek bir `.py` dosyası çalıştırılarak (Self-contained) ayağa kalkmalıdır. Tüm HTML, CSS ve JS kodları bu dosya içinde gömülü (inline) kalmaya devam etmelidir.
- **Kütüphane Kullanımı:** Proje modern kütüphanelere (FastAPI, Flask, SQLAlchemy vb.) açıktır ancak bu paketler `requirements.txt` dosyasında listelenmelidir. Uygulama modüler parçalara ayrılsa bile, son çalışma aşamasında (runtime) taşınabilirliği korumak için tek bir ana dosyadan yönetilmelidir.
- **Frontend Gelişimi:** UI kütüphaneleri kullanılabilir, fakat nihai çıktı (bundle) Python dosyası içine gömülerek "tek dosya ile çalıştırma" özelliği korunmalıdır.

## 🛡️ Kritik Fonksiyonel Kurallar (Hata Önleyici)
- **Durum Sistemi (V3):**
    - Yeni durumlar: "Bitti", "Yarım Kaldı", "Bitmedi ama çalışıyor", "Pasif", "Arşiv".
    - İstatistikler: "Devam Eden" sayısı, "Yarım Kaldı" ve "Bitmedi ama çalışıyor" durumlarının toplamıdır.
- **Taslak Sistemi (V6):** 
    - Taslaklar `localStorage`'da `proje_taslak` anahtarıyla tutulur. 
    - **Debounce:** Yazım sırasında 300ms gecikme ile kaydedilir.
    - **Guard:** Taslak kaydı işlemi **asla** `modalKapat` fonksiyonu içinde veya sonrasında tetiklenmemelidir.
- **Modal Güvenliği:** 
    - Input alanında metin seçerken mouse dışarı kayarsa modalın kapanmaması için `mousedown` ve `click` overlay üzerinde çapraz kontrol edilir. Bu mantığı bozmayın.
- **Veritabanı:** 
    - Migrasyonlar `tablolari_olustur` içinde `try-except` bloklarıyla `ALTER TABLE` şeklinde yapılmalıdır.

## 📂 Önemli Dosyalar ve Konumlar
- `ide_yonetici.py`: Tüm uygulama (Backend + Frontend) buradadır.
- `ide_yonetici.db`: SQLite veritabanı (script ile aynı dizinde).
- `PROJE_TEST_SUITE.py`: Backend bütünlük testleri.
- `dist/IDE_Yonetici.exe`: PyInstaller ile üretilen taşınabilir sürüm.

## 🚀 İş Akışı ve Doğrulama
1.  **Geliştirme:** `ARAYUZ_HTML` değişkeni içindeki JS/CSS kodlarını güncelleyin.
2.  **Yenileme:** Değişikliklerin yansıması için Python sürecini durdurup (`Ctrl+C`) tekrar başlatın. Tarayıcıda `Ctrl+F5` yapın.
3.  **Test:** `python PROJE_TEST_SUITE.py` komutunu çalıştırın.
4.  **Tanılama:** Uygulama içindeki `/api/diagnostic` uç noktasının "Healthy" döndüğünü doğrulayın.

## ⚠️ Bilinen "Gotcha"lar
- **Port Çakışması:** Sunucu `8700` meşgulse otomatik olarak portu artırır. API isteklerinde portun dinamik olabileceğini unutmayın.
- **Lokal Dizin:** Projelerdeki "Lokal Dizin" yolu `subprocess` ile açılırken Windows yol formatına (backslashes) dikkat edilmelidir.
