# Product Requirements Document (PRD) - IDE Proje Takip Sistemi v3.0

**Proje Adı:** IDE Proje Takip Sistemi (Modernize Sürüm)  
**Sürüm:** 3.0 (Ölçeklenebilir & Zengin Özellikli)  
**Hedef:** Mevcut minimalist yapıyı modern kütüphanelerle güçlendirerek profesyonel bir araç haline getirmek.

---

## 1. Mimari Değişim Önerileri ve Kritik Kısıtlamalar

Uygulamanın ölçeklenebilirliğini artırmak için modern kütüphaneler kullanılırken aşağıdaki **en yüksek öncelikli** kısıtlamaya uyulmalıdır:

> **Kritik Kısıtlama:** Uygulama ne kadar modernize edilirse edilsin, son kullanıcı sistemi tek bir `.py` dosyasını çalıştırarak ayağa kaldırabilmelidir. Tüm frontend varlıkları (assets) ve backend mantığı bu ana dosyada (self-contained) toplanmalıdır.

### 1.1. Backend (Python)
- **FastAPI:** `http.server` yerine kullanılacak. Otomatik dökümantasyon (Swagger), yüksek hız ve tip güvenliği sağlar.
- **SQLAlchemy / SQLModel:** SQLite veritabanı işlemlerini daha güvenli ve esnek hale getirmek için.
- **Pydantic:** Veri doğrulama ve şema yönetimi için.
- **Uvicorn:** ASGI sunucusu olarak FastAPI'yi çalıştırmak için.
- **PyJWT:** Kullanıcı kimlik doğrulama (Auth) mekanizması eklemek için.

### 1.2. Frontend
- **React + Vite:** Mevcut Vanilla JS'ten bileşen tabanlı (component-based) bir yapıya geçiş için.
- **Tailwind CSS:** Tasarımı çok daha hızlı ve profesyonel bir şekilde yönetmek için.
- **Axios:** API isteklerini daha kolay yönetmek ve hata kontrolü yapmak için.

---

## 2. Yeni Fonksiyonel Gereksinimler (V3.0)

### 2.1. Kimlik Doğrulama ve Güvenlik (Auth)
- **Login Ekranı:** Uygulamanın sadece yetkili kullanıcı tarafından açılabilmesi için yerel veya bulut tabanlı bir giriş sistemi.
- **Token Tabanlı İletişim:** API isteklerinin JWT ile güvenli hale getirilmesi.

### 2.2. Gelişmiş Bulut Senkronizasyonu
- **Cloud Sync:** Veritabanının isteğe bağlı olarak bir bulut veritabanı (Supabase, Firebase vb.) ile eşitlenmesi. Bu sayede farklı bilgisayarlardan aynı verilere erişim sağlanacak.
- **Export/Import Geliştirmeleri:** JSON'un yanı sıra Excel ve CSV formatlarında dışa aktarım desteği.

### 2.3. Bildirim ve Hatırlatıcılar
- **Masaüstü Bildirimleri:** Bulut IDE limitleri veya yaklaşan son tarihler için `plyer` veya benzeri paketler ile Windows bildirimleri gönderilmesi.
- **Zaman Ayarlı Notlar:** Belirli bir tarihte hatırlatılması gereken proje notları.

### 2.4. Dosya Sistemi Entegrasyonu (Advanced)
- **Watchdog:** Yerel proje dizinlerindeki değişiklikleri (son dosya güncelleme tarihi vb.) otomatik takip ederek dashboard'da sergileme.

---

## 3. Teknik Gereksinimler (NFR)

- **Performans:** FastAPI'nin asenkron yapısı sayesinde eşzamanlı işlemler daha hızlı gerçekleştirilecek.
- **Modülerlik:** Klasör yapısı `backend/` ve `frontend/` olarak ayrılarak projenin yönetimi kolaylaştırılacak.
- **Güvenlik:** API uç noktaları korumalı hale getirilecek ve veri girişleri Pydantic ile sanitize edilecek.
- **Taşınabilirlik (Portability):** Tüm bağımlılıklar (`requirements.txt`) yüklendikten sonra, uygulama tek bir ana dosya üzerinden (`main.py` veya `ide_yonetici.py`) sorunsuz çalışmalıdır.

---

## 4. Yol Haritası (Roadmap)

1.  **Backend Refactor:** Mevcut `ide_yonetici.py` içindeki mantığı FastAPI ve SQLAlchemy'ye taşıma.
2.  **API Migration:** Mevcut API yollarını (`/api/projeler` vb.) yeni standartlarla güncelleme.
3.  **Frontend Modernization:** Vite/React kurulumu ve mevcut UI'ın Tailwind ile yeniden tasarlanması.
4.  **Auth Integration:** Kullanıcı giriş ve güvenlik katmanının eklenmesi.
5.  **Cloud Sync:** Opsiyonel senkronizasyon özelliklerinin devreye alınması.
