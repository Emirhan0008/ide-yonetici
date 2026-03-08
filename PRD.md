# Product Requirements Document (PRD)

**Proje Adı:** IDE Proje Takip Sistemi  
**Sürüm:** 2.0 (MVP Odaklı)  
**Tarih:** 08.03.2026

---

## 1. Giriş

### 1.1. Amaç
IDE Proje Takip Sistemi, geliştiricilerin lokal ve bulut tabanlı geliştirme ortamlarındaki projelerini kolayca organize etmesini sağlayan hafif, açık kaynak görünümlü bir yönetim aracıdır. Özellikle ücretsiz (free-tier) bulut IDE kullanımından doğan limitler (günlük, aylık kotalar vb.) nedeniyle farklı hesaplarda veya farklı platformlarda açılan projelerin izini sürmek, projenin durumu ve varsa hangi bağlantı adresi (URL) üzerinden erişilebildiği gibi kritik bilgileri tek ekranda toplamak temel amacı teşkil eder.

### 1.2. Hedef Kitle (Kullanıcılar)
- Aynı anda birden fazla IDE kullanan geliştiriciler (Örn: Cursor, VS Code).
- Bulut IDE'leri yoğun kullanan ve kota sınırlarına takıldığı için projelerini farklı hesaplarda yarım bırakan geliştiriciler (Cloud9, Firebase Studio, Replit, StackBlitz).
- Projelerine "Kişisel", "İş", "Test" gibi farklı e-posta hesaplarıyla erişim sağlayan kişiler.

---

## 2. Kullanıcı Hikayeleri (User Stories)

- **US01:** Geliştirici olarak, sistemde yeni bir proje oluşturabilmeli; projenin adını, hangi IDE'de/hesapta bulunduğunu, durumunu (aktif, pasif, arşiv) ve projenin URL'sini (bulut ise) girebilmeliyim ki ihtiyacım olduğunda projeye hızlıca erişebileyim.
- **US02:** Geliştirici olarak, tek bir ekranda tüm projelerimi kart (card view) veya liste şeklinde görebilmeliyim ki durumlarını genel olarak anlayabileyim.
- **US03:** Geliştirici olarak, projelerime notlar ekleyebilmeliyim (ör: "Günlük limiti bitti yarın devam et" veya "Şu tarihe kadar ücretsiz").
- **US04:** Geliştirici olarak, projeleri IDE türüne (Bulut/Lokal), Durumuna (Aktif/Arşiv) ve arama çubuğu üzerinden proje/hesap ismine göre filtreleyebilmeliyim.
- **US05:** Geliştirici olarak, sık kullandığım IDE'leri (Cursor, VS Code) ve hesaplarıma ait isimleri/e-postaları tek seferlik tanımlayabilmeliyim (Auto-complete/Settings) ki her seferinde tekrar tekrar adres, isim yazmak zorunda kalmayayım.
- **US06:** Geliştirici olarak, uygulamayı kullanabilmek için ek veritabanı veya karmaşık kurulumlarla uğraşmamalıyım. `.py` dosyasını çalıştırır çalıştırmaz, modern bir arayüzle karşılaşmalıyım.

---

## 3. Fonksiyonel Gereksinimler

### 3.1. Ana Sayfa (Dashboard)
- **FR01. İstatistikler:** Ana ekranda projelerin sayısını (toplam ve aktif olmak üzere), ekli farklı IDE sayılarını ve farklı hesap sayılarını özet bir şekilde (stat cards) göstermelidir.
- **FR02. Kart Görünümü (Listeleme):** Veritabanından gelen tüm projeleri okunaklı bir grid sisteminde, rozetler (tags) ile (Örn: ☁️ Bulut, 🖥️ Lokal, ✅ Aktif vb.) destekleyerek kullanıcıya sunmalıdır.
- **FR03. Arama Çubuğu ve Filtreler:** Eklenen projeler içerisinde isim, hesap veya notlar üzerinden dinamik arama yapabilmeli ve formdaki dropdownlar yardımı ile anında "Durum" veya "IDE Türü" filtrelemesi uygulanabilmelidir.

### 3.2. Proje Ekleme/Düzenleme Ekranı (Form)
- **FR04. Tekil Form Akışı:** Eskiden olduğu gibi farklı sekmeler yerine modal tabanlı tek bir form ekranında hem proje detayları, hem de hangi IDE ve hesapta barındığı girilebilmelidir.
- **FR05. Veri Bağlama (Otomatik Tamamlama):** Formda IDE adı ve hesap kısmına tıklanıldığında `<datalist>` HTML etiketi yardımı ile eskiden eklenmiş ya da ayarlardan gelen hazır ifadeler kullanıcıya önerilmelidir.
- **FR06. Form Validasyon:** Form, gönderilmeden önce proje isminin girilip girilmediğini kontrol etmelidir.

### 3.3. Ayarlar (Ön Tanımlama) Bölümü
- **FR07. Önceden IDE/Hesap Ekleme:** Navbar üzerinde bir ayar (⚙) ikonuna basılarak bir modal açılması tetiklenmeli ve buralara yeni IDE veya yeni hesap eklenebilmelidir (CRUD işlemi).
- **FR08. Ayarların Saklanması:** Eklenen tanımlı IDE'ler `tanimli_ideler` tablosunda ve hesaplar `tanimli_hesaplar` tablosunda tutulmalıdır. Silme işleminin `projeler` tablosunu olumsuz etkilemiyor (ilişkisel cascade hatalarından kaçınma amaçlı string tabanlı saklama) olması lazımdır.

### 3.4. API ve Veritabanı
- **FR09. Veritabanı Mimarisi:** Arka planda Python `sqlite3` modülü kullanılarak tek bir `ide_yonetici.db` dosyasıyla CRUD operasyonları yürütülmelidir.
- **FR10. Gömülü HTTP Sunucusu:** Tüm sayfa içeriği ve API uç noktaları `http.server.BaseHTTPRequestHandler` ile ayağa kaldırılmalı ve CORS uyumlu çalışmalıdır (`GET`, `POST`, `PUT`, `DELETE`).
- **FR11. Port Mekanizması:** Python sunucusu `8700` numaralı portta çalışmalıdır. Port meşgulse `8701` gibi +1 deneyerek müsait birini bulmalı ve sistemi kitlenmekten korumalıdır.

---

## 4. Teknik/Fonksiyonel Olmayan Gereksinimler (NFR)

- **Performans:** Uygulama bir web tarayıcısı üzerinden maksimum 1 veya 2 saniyede verileri yüklemelidir. (Zaten SQLite kullanıldığı için okuma hızları yeterince iyi).
- **Taşınabilirlik (Portability):** Uygulama `ide_yonetici.py` adı altındaki gömülü string yapısı sayesinde dışarıya bağımlılık (Node, npm, pip requirements) hissettirmemeli, her platformda (Windows/Mac/Linux) yalnızca Python ve standart paketler kullanılarak rahatça kurulabilmelidir.
- **UX/UI Kalitesi:** Modern, cam efektleri (glassmorphism), neon/koyu tema (dark mode focused), animasyon destekli (toast notification, modal slideUp), responsive ve kullanıcı efora dayanan minimal bir yapı tasarımında olmalıdır. Web UI, modern cihazlar için (masaüstü/ mobil uyumlu ama asıl hedef masaüstü tarayıcı) olmalıdır.

---

## 5. Çözüm Mimarisinin Veri Yapısı (Schema Özeti)

1. **`projeler` Tablosu:** Uygulama üzerinde sergilenen temel odak. (id, proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, durum, notlar ...)
2. **`tanimli_ideler` Tablosu:** Proje eklerken veritabanından çekilip hızlı auto-complete doldurması yapan kütük liste. (id, ide_adi, ide_turu, ide_url)
3. **`tanimli_hesaplar` Tablosu:** Proje eklerken veritabanından çekilip hızlı auto-complete doldurması yapan kütük liste. (id, hesap_adi, hesap_email)

---

## 6. Sürüm Planı (Roadmap / Gelecek Hedefler)

**MVP + Hedeflenen (Şu anki geliştirme):**
- [x] Tek sayfa uygulaması (Single Page App - SPA)
- [x] Python entegre DB ve Server ayağa kalkışı
- [x] Modern UI tasarımı ve tek tuşla (CLI) çalıştırma.
- [x] Projenin notlarına ve durumuna göre detaylı takip edilebilmesi.
- [x] IDE ve Hesap Ön tanımlama işlemleri (Settings).

**V3 Planlaması:**
- [ ] Uygulamaya kimlik doğrulama veya şifreli koruma mekanizmasının getirilmesi.
- [ ] Farklı bilgisayarlarda kullanıldığında aynı veritabanına erişim için bir tür "Sync" (Senkronizasyon) veya dışa aktarım seçenekleri (Import/Export JSON/CSV).
- [ ] Projelerde etiket (tag) veya renk bazlı ek sınıflandırmalar yapılması.
