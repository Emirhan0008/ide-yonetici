# Minimum Viable Product (MVP) - IDE Proje Takip Sistemi

## 1. Proje Özeti
IDE Proje Takip Sistemi, geliştiricilerin farklı bulut tabanlı ve lokal geliştirme ortamlarındaki (IDE) projelerini tek bir merkezden takip edebilmelerini sağlayan hafif, hızlı ve modern bir web tabanlı yerel masaüstü uygulamasıdır.

## 2. Temel Problem
Geliştiriciler genellikle lokal IDE'lerin (VS Code, Cursor vs.) yanı sıra çeşitli bulut tabanlı geliştirme platformlarını (Replit, Firebase Studio, StackBlitz vb.) kullanmaktadır. Özellikle ücretsiz planlardaki limitler nedeniyle farklı platformlarda veya farklı hesaplar altında projelere devam etme ihtiyacı doğmaktadır. Bu da zamanla "Hangi projenin güncel hali hangi IDE'de ve hangi hesaptaydı?" karmaşasına yol açmaktadır.

## 3. MVP Kapsamı (Temel Özellikler)

MVP (Minimum Viable Product) aşamasında uygulama aşağıdaki temel özellikleri barındırmalıdır:

### 3.1. Proje Yönetimi (Tek Form Odaklı)
Tüm veriler projeler odaklı olarak tek bir formda toplanır.
- **Proje Adı:** Projenin genel adı.
- **IDE Bilgileri:** Projenin bulunduğu platform/IDE adı, türü (Lokal/Bulut) ve URL'si.
- **Hesap Bilgileri:** Hangi kullanıcı hesabı veya e-posta ile o platforma giriş yapıldığı.
- **Durum:** Projenin aktif, pasif veya arşivde olma durumu.
- **Notlar:** Projeyle ilgili kısıtlamalar (örn: günlük limit bitti vb.) veya hatırlatmalar.

### 3.2. Merkezi Dashboard (Arayüz)
- Modern, koyu temalı, tarayıcıda çalışan şık bir kart görünümü.
- Üstte hızlı metrikler (Toplam Proje, Aktif, Farklı IDE, Farklı Hesap sayıları).
- Liste üzerinde kelime ile arama ve filtreleme (Duruma, IDE türüne veya IDE adına göre) imkanı.

### 3.3. Ayarlar (Ön Tanımlı Veriler)
- Sık kullanılan IDE'lerin ve Hesapların önceden sisteme kaydedilmesi.
- Yeni proje eklerken veya düzenlerken, önceden kaydedilen IDE'lerin ve hesapların form alanlarında otomatik tamamlama (autocomplete) ile önerilmesi.

### 3.4. Kalıcı Yerel Veritabanı
- Harici bir sunucu kurulumu gerektirmeksizin, projeyle aynı dizinde çalışan gömülü **SQLite** veritabanı.
- Çift tıklama ile çalışıp verilerin doğrudan dosyaya yazılması (`ide_yonetici.db`).

## 4. Teknik Altyapı
- **Backend:** Python (Standart kütüphaneler: `http.server`, `sqlite3`, `webbrowser`). Hiçbir harici pip paketi (Flask/Django vb.) gerekmez.
- **Frontend:** HTML5, CSS3 (Modern Glassmorphism, CSS Variables), Vanilla JavaScript. Tüm kod Python dosyası içine metin (string) olarak gömülüdür.
- **Çalışma Şekli:** `.py` dosyası çalıştırıldığında Python yerel bir API sunucusu ayağa kaldırır ve varsayılan tarayıcıda uygulamayı otomatik açar.

## 5. Kapsam Dışı Olacaklar (Post-MVP)
- Çoklu kullanıcı desteği ve şifreli giriş.
- Verilerin uzak bir sunucu veya bulut (Cloud) ile senkronizasyonu.
- Bildirimler (Push notifications vb.).
- Detaylı loglama veya aktivite geçmişi (History) izleme detayları.
