# 🛠️ IDE Proje Takip Sistemi v2.0

Bulut (Cursor, Replit, Cloud9 vb.) ve lokal geliştirme ortamlarındaki projelerinizi tek merkezden yönetmenizi sağlayan, hafif ve modern bir takip aracı.

![IDE Yönetici](https://img.shields.io/badge/Version-2.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.x-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

---

## 🚀 Öne Çıkan Özellikler

*   **⚡ Modern Arayüz:** Glassmorphism tasarımı, Electric Blue tema ve akıcı animasyonlar.
*   **💾 Gelişmiş Taslak Sistemi (V6):** Yazdığınız hiçbir şey kaybolmaz! Modal kapansa bile otomatik kayıt ve geri yükleme.
*   **💻 Çoklu IDE ve Hesap Desteği:** Projelerinizi hangi e-posta veya hangi IDE (Bulut/Lokal) üzerinde bıraktığınızı asla unutmayın.
*   **🔍 Akıllı Filtreleme:** Proje adına, IDE türüne veya durumuna (Aktif/Arşiv) göre anında arama.
*   **📦 Sıfır Bağımlılık:** Sadece standart Python kütüphaneleriyle çalışır. `pip install` derdi yok!
*   **🛠️ Entegre Araçlar:** Veritabanı yedeği alma (Export/Import), diagnostic raporu ve hafıza temizleme özellikleri.

## 🛠️ Kurulum ve Çalıştırma

### 1. Python ile Çalıştırma
Bilgisayarınızda Python yüklü ise projeyi doğrudan başlatabilirsiniz:

```bash
python ide_yonetici.py
```
*Sistem otomatik olarak varsayılan tarayıcınızda `http://localhost:8700` adresini açacaktır.*

### 2. Standart Kullanım (.exe)
Eğer Python yüklü değilse veya terminalle uğraşmak istemiyorsanız:
`dist/` klasörü içindeki **IDE_Yonetici.exe** dosyasını çalıştırın.

---

## 🧪 Geliştiriciler İçin

Uygulama tescilli bir **Antigravity Kit** projesidir.

*   **Test Etme:** `python PROJE_TEST_SUITE.py` komutuyla backend sağlığını kontrol edebilirsiniz.
*   **Build Alma:** Kendi .exe dosyanızı oluşturmak için:
    ```bash
    pyinstaller --onefile --name "IDE_Yonetici" --clean ide_yonetici.py
    ```
*   **Akıllı Dökümantasyon:** Proje mimarisi ve teknik detaylar için [agent.md](agent.md) dosyasını inceleyin.

---

## 📄 Lisans
Bu proje MIT lisansı ile korunmaktadır. Özgürce kullanılabilir ve geliştirilebilir.

---
*Geliştiriciler tarafından, geliştiriciler için tasarlandı.*
