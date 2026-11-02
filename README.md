# 🛠️ IDE Proje Takip Sistemi v3

Bulut (Cursor, Replit, Cloud9 vb.) ve lokal geliştirme ortamlarındaki projelerinizi tek merkezden yönetmenizi sağlayan, hafif ve modern bir takip aracı.

![Version](https://img.shields.io/badge/Version-3.0-blue?style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-Vite_+_%232F74C0?style=for-the-badge&logo=typescript&logoColor=white)
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

### 3. Web Uygulaması (Vite + TypeScript) — CANLI KAYNAK
Arayüz `app/` altında modüler bir Vite + TypeScript projesidir ve Firebase Hosting üzerinden yayınlanır:

```bash
cd app
npm install        # ilk sefer
npm run dev        # geliştirme: http://localhost:5199
npm test           # Playwright duman testleri (8 senaryo)
npm run build      # üretim çıktısı: app/dist
firebase deploy --only hosting   # repo kökünden yayın
```
- `https://ideyonetici.web.app` adresinden erişilir.
- Veriler kullanıcının Google hesabı ile Firebase Realtime Database'de izole edilir (`users/$uid` kuralları).
- Kimlik doğrulama Firebase Auth (Google) ile doğrudan yapılır; backend yoktur.
- Cache: HTML `no-store`, hash'li asset'ler (`/assets/*`) 1 yıl `immutable` — güncellemede yalnızca değişen dosya iner.

### 4. Cloud Run (Backend) — KALDIRILDI
`cloudrun/` klasörü kaldırıldı. Backend ihtiyacı yoktur; veriler Firebase Realtime Database'de tutulur.

---

## 🧪 Geliştiriciler İçin

*   **Build Alma:** `cd app && npm run build` → çıktı `app/dist` (firebase.json buradan yayınlar).

*   **Tanılama:** Backend yoktur. Uygulama içi Ayarlar → Veri sekmesi, Firebase hesabını ve buluttaki veri sayılarını gösterir.

*   **Akıllı Dökümantasyon:** Proje mimarisi, fonksiyonel kurallar ve "gotcha"lar için [agent.md](agent.md) dosyasını inceleyin.

*   **Eski PRD:** Uygulanmamış v3.0 planı (FastAPI/React/Tailwind önerisi) [docs/archive/PRD-v3.0-uygulanmamis.md](docs/archive/PRD-v3.0-uygulanmamis.md) altındadır.

---

## 📂 Proje Yapısı

```
.
├── app/                    # CANLI KAYNAK — Vite + TypeScript uygulaması
│   ├── src/
│   │   ├── data/           # TEK veri kapısı (RTDB) — projeler, tanimlilar, gorseller
│   │   ├── ui/             # kartlar, modal, ayarlar, tema, dom yardımcıları
│   │   ├── styles/         # tema / kartlar / modal / ayarlar / cila CSS modülleri
│   │   ├── model.ts        # Alan tipleri + durum kuralları
│   │   └── store.ts        # Tipli durum deposu (abone ol / setState)
│   ├── e2e/                # Playwright duman testleri (npm test)
│   └── dist/               # Build çıktısı (firebase.json buradan yayınlar)
├── firebase.json           # Firebase Hosting + RTDB config
├── database.rules.json     # Firebase RTDB güvenlik kuralları
├── agent.md                # Teknik hafıza / AI ajan yönergeleri
├── README.md               # Bu dosya
├── docs/archive/           # Eski PRD'ler + arşivlenen tek dosya v2.5 + masaüstü uygulaması
└── yedekler/               # Eski otomatik JSON yedekler (git-ignored, dış arşive taşınır)
```

---

## 📄 Lisans

Bu proje MIT lisansı ile korunmaktadır. Özgürce kullanılabilir ve geliştirilebilir.

---

*Geliştiriciler tarafından, geliştiriciler için tasarlandı.*
