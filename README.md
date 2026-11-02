# 🛠️ IDE Proje Takip Sistemi v2.5

Bulut (Cursor, Replit, Cloud9 vb.) ve lokal geliştirme ortamlarındaki projelerinizi tek merkezden yönetmenizi sağlayan, hafif ve modern bir takip aracı.

![Version](https://img.shields.io/badge/Version-2.5-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.x-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

---

## 🚀 Öne Çıkan Özellikler

*   **⚡ Modern Arayüz:** Glassmorphism tasarımı, Electric Blue / Soft Light tema, light/dark mod desteği ve akıcı animasyonlar.
*   **💾 Gelişmiş Taslak Sistemi (V6):** Yazdığınız hiçbir şey kaybolmaz! Otomatik kayıt ve korumalı geri yükleme.
*   **📊 Detaylı Durum Yönetimi:** "Bitti", "Yarım Kaldı", "Bitmedi ama çalışıyor", "Pasif", "Arşiv" durumları ve "Devam Eden" toplamı.
*   **🎨 Dinamik Görsellik:** IDE ismine göre otomatik değişen ikonlar ve renkli kart kenarlıkları, kart görseli (Base64) desteği.
*   **🔍 Akıllı Arama:** Aranan kelimelerin metin içinde vurgulanması (Highlight).
*   **☁️ Firebase Sync (V2.5):** Veriler `zlib` (level 9) ile sıkıştırılıp base64 olarak Firebase Realtime Database'e yazılır. Tipik tasarruf: %60-75.
*   **🛠️ Entegre Araçlar:** JSON yedekleme (Export/Import), diagnostic raporu, hafıza temizleme, IDE/Hesap tanımlama yöneticisi.

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Python ile Çalıştırma (Masaüstü) — ARŞİVLENDİ
`ide_yonetici.pyw` masaüstü uygulaması `docs/archive/` altına taşındı. Canlı sürüm yalnızca Firebase Hosting (`public/index.html`) üzerinden çalışır.

### 2. Standalone Executable — ARŞİVLENDİ
Masaüstü `.exe` üretimi kaldırıldı (`build/` yalnızca geçmiş çıktıları içerir).

### 3. Firebase Hosting (Sadece Web Arayüzü)
Frontend public build'i Firebase Hosting üzerinden yayınlanır:

```bash
firebase deploy --only hosting
```
- `https://ideyonetici.web.app` adresinden erişilir.
- Veriler kullanıcının Google hesabı ile Firebase Realtime Database'de izole edilir (`users/$uid` kuralları).
- Kimlik doğrulama `public/index.html` içindeki Firebase Auth shim'i üzerinden yapılır.

### 4. Cloud Run (Backend) — KALDIRILDI
`cloudrun/` klasörü kaldırıldı. Backend ihtiyacı yoktur; veriler Firebase Realtime Database'de tutulur.

---

## 🧪 Geliştiriciler İçin

*   **Build Alma:** Masaüstü build kaldırıldı. Arayüz değişikliği için `public/index.html` düzenlenip `firebase deploy --only hosting` yapılır.

*   **Tanılama:** Backend yoktur. Uygulama içi Ayarlar panelindeki tanı bilgisi, `public/index.html` içindeki CloudShim'in Firebase Realtime Database bağlantısının durumunu gösterir.

*   **Akıllı Dökümantasyon:** Proje mimarisi, fonksiyonel kurallar ve "gotcha"lar için [agent.md](agent.md) dosyasını inceleyin.

*   **Eski PRD:** Uygulanmamış v3.0 planı (FastAPI/React/Tailwind önerisi) [docs/archive/PRD-v3.0-uygulanmamis.md](docs/archive/PRD-v3.0-uygulanmamis.md) altındadır.

---

## 📂 Proje Yapısı

```
.
├── public/index.html       # Frontend (Firebase Hosting için — tek canlı kaynak)
├── firebase.json           # Firebase Hosting + RTDB config
├── database.rules.json     # Firebase RTDB güvenlik kuralları
├── agent.md                # Teknik hafıza / AI ajan yönergeleri
├── README.md               # Bu dosya
├── docs/archive/           # Eski PRD'ler, planlar + arşivlenen masaüstü uygulaması (ide_yonetici.pyw)
└── yedekler/               # Otomatik JSON yedekler (git-ignored, dış arşive taşınır)
```

---

## 📄 Lisans

Bu proje MIT lisansı ile korunmaktadır. Özgürce kullanılabilir ve geliştirilebilir.

---

*Geliştiriciler tarafından, geliştiriciler için tasarlandı.*
