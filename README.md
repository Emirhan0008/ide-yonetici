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

### 1. Python ile Çalıştırma (Masaüstü)
Bilgisayarınızda Python 3.x yüklü ise:

```bash
python ide_yonetici.pyw
```
*Sistem otomatik olarak varsayılan tarayıcınızda `http://localhost:8700` adresini açacaktır (port meşgulse otomatik artırılır).*

`ide_yonetici.pyw` self-contained bir dosyadır: tüm HTML/CSS/JS frontend kodu `public/index.html` ile senkronize olarak içinde gömülüdür. Hiçbir `pip install` gerekmez; yalnızca standart kütüphane kullanılır.

### 2. Standalone Executable
`build/` klasörü içindeki **IDE_Yonetici.exe** dosyasını çalıştırın. Python gerektirmez.

### 3. Firebase Hosting (Sadece Web Arayüzü)
Frontend public build'i Firebase Hosting üzerinden yayınlanır:

```bash
firebase deploy --only hosting
```
- `https://ideyonetici-em-2026.web.app` adresinden erişilir.
- Veriler kullanıcının Google hesabı ile Firebase Realtime Database'de izole edilir (`users/$uid` kuralları).
- Kimlik doğrulama `public/index.html` içindeki Firebase Auth shim'i üzerinden yapılır.

### 4. Cloud Run (Backend)
Python backend `cloudrun/` altında containerize edilip Cloud Run'a deploy edilebilir:

```bash
cd cloudrun
gcloud run deploy ide-yonetici --source .
```
Endpoint: `/api/projeler`, `/api/diagnostic`, vb.

---

## 🧪 Geliştiriciler İçin

*   **Build Alma:** Kendi .exe dosyanızı oluşturmak için:
    ```bash
    pyinstaller --onefile --name "IDE_Yonetici" --clean ide_yonetici.pyw
    ```
    Çıktı: `build/IDE_Yonetici.exe`

*   **Tanılama:** Backend'in ayakta olduğunu `/api/diagnostic` uç noktasından doğrulayın.

*   **Akıllı Dökümantasyon:** Proje mimarisi, fonksiyonel kurallar ve "gotcha"lar için [agent.md](agent.md) dosyasını inceleyin.

*   **Eski PRD:** Uygulanmamış v3.0 planı (FastAPI/React/Tailwind önerisi) [docs/archive/PRD-v3.0-uygulanmamis.md](docs/archive/PRD-v3.0-uygulanmamis.md) altındadır.

---

## 📂 Proje Yapısı

```
.
├── ide_yonetici.pyw        # Self-contained masaüstü uygulaması (Python + PyWebView)
├── public/index.html       # Frontend (Firebase Hosting için)
├── cloudrun/               # Cloud Run deployment (Docker + main.py)
├── firebase.json           # Firebase Hosting + RTDB config
├── database.rules.json     # Firebase RTDB güvenlik kuralları
├── agent.md                # Teknik hafıza / AI ajan yönergeleri
├── README.md               # Bu dosya
├── docs/archive/           # Eski PRD'ler, planlar
├── build/, dist/           # PyInstaller çıktıları (git-ignored)
└── yedekler/               # Otomatik JSON yedekler (git-ignored, dış arşive taşınır)
```

---

## 📄 Lisans

Bu proje MIT lisansı ile korunmaktadır. Özgürce kullanılabilir ve geliştirilebilir.

---

*Geliştiriciler tarafından, geliştiriciler için tasarlandı.*
