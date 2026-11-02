# 🤖 Yapay Zeka & Geliştirici Bilgi Merkezi (agent.md)

Bu dosya, projeyi devralacak olan yazılımcı veya yapay zeka ajanı için kritik teknik hafızayı ve operasyonel kuralları içerir. **Lütfen geliştirmeye başlamadan önce okuyun.**

## 🎯 Proje Vizyonu ve Durumu
Bu araç, çoklu bulut IDE (Cursor, Replit vb.) kullanımından doğan "hangi proje hangi hesapta/IDE'de kaldı?" karmaşasını çözen minimalist bir yönetim panelidir. Şu an **V2.5 (Stabil)** aşamasındadır.

## 🛠️ Teknik Mimari (GÜNCEL — V2.5 shim dönemi)
- **CANLI KAYNAK:** `public/index.html` — tek dosya (HTML + CSS + JS, ~2.350 satır). Firebase Hosting üzerinden yayınlanır: `https://ideyonetici.web.app`.
- **BACKEND YOK.** Eski Python masaüstü uygulaması (`docs/archive/ide_yonetici.pyw`) ve Cloud Run backend'i kaldırıldı.
- **CloudShim (kritik kavram):** UI kodu tarihsel nedenlerle hâlâ `Utils.api('/api/...')` çağrıları kullanır. `index.html` içindeki shim (bkz. `[CloudShim] yüklendi` log'u, ~satır 2000+) bu fonksiyonu override edip çağrıları **doğrudan Firebase Realtime Database / Auth**'a yönlendirir:
  - `GET /api/projeler` → `db.ref('users/$uid/projeler').once('value')`
  - `POST` → `ref.push()`, `PUT` → `ref.update()`, `DELETE` → `ref.remove()`
  - `/api/auth/google` → `firebase.auth().signInWithCredential(...)`
  - `/api/istatistikler` → backend'e gitmez, bellekte hesaplanır.
  - `BACKEND_ONLY` listesindeki yollar (bulut/yedekle vb.) bilerek hata fırlatır.
- **Firebase SDK:** compat 10.7.1, CDN'den yüklenir (firebase-app / auth / database).
- **Deploy:** `firebase deploy --only hosting` (Firebase projesi: `ideyonetici-em-2026`).

### Yol haritası — DURUM: Faz 1 tamam (iskelet `app/` altında)
Vite + vanilla TypeScript'e geçiş sürüyor. **Faz 1 inşa edildi:**
- `app/` = bağımsız Vite projesi (`npm run dev` / `npm run build`, çıktı `app/dist`).
- `src/firebase.ts` modular SDK v13 · `src/model.ts` tipler · `src/store.ts` tipli state · `src/auth.ts` popup+redirect giriş · `src/data/` tek veri kapısı (projeler, tanimlilar, gorseller, rtdb yardımcıları).
- `data/gorseller.ts` Faz 2 boru hattını içeriyor: `gorseliKucult` (800px JPEG) + ayrı `users/$uid/gorseller/$projeId` yolu + `gorselleriGocEt` (bir defalık migration).
- RTDB şeması değişmedi; canlı site hâlâ `public/index.html`. **Flag day:** Faz 3 UI taşınımı bitince `firebase.json` → `public: "app/dist"`, eski dosya `docs/archive/`'e.
- **Faz 3 ilk dilim tamam:** `app/src/ui/` (dom, renkler, tema, kartlar, modal) + tam `index.html` + `styles/` (tema/kartlar/modal CSS). Kart ızgarası, arama+vurgulama, durum/tür/IDE/sahiplik filtreleri, 7 istatistik, ekle/düzenle/sil modalı, taslak (V6), kart rengi popup, silme onayı, tema, tembel görsel yükleme — hepsi `data/` kapısından geçiyor. Canlı tarayıcı smoke testleri (Playwright) geçti: render, arama, filtre, modal-dolu, tema, mobil grid, tırnaklı ad (güvenli delegasyon).
- Kalan Faz 3: Ayarlar paneli (IDE/hesap CRUD, JSON export/import, app arka planı), `gorselleriGocEt` için tetikleyici UI, avatar dropdown'ına Ayarlar girişi. Sonra Faz 4 (hedefli DOM + Playwright smoke testleri + flag day: `firebase.json` public → `app/dist`).

## 🗄️ Veri Katmanı (Firebase RTDB)
- Kök: `users/$uid/` (rules: yalnızca kendi uid'sini okur/yazar — `database.rules.json`).
- Alt yollar: `projeler/`, `ideler/`, `hesaplar/` (RTDB push-key'li nesne dizisi; `objeToArray()` ile diziye çevrilir, `id` alanı key'den gelir).
- Proje alanları: `proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, durum, sahiplik, notlar, etiketler, lokal_yol, deploy_url, kart_rengi, kart_gorseli, olusturma_tarihi, guncelleme_tarihi`.
  - `kart_gorseli`: base64 data-url. **Not:** shim döneminde RTDB'ye yazılıyor (eski backend'de yazılmazdı). Vite geçişinde ayrı `users/$uid/gorseller/$projeId` yoluna + istemci tarafı küçültmeye taşınacak (Faz 2).
  - `kart_rengi`: boşsa duruma göre otomatik renk.
- Uygulama arka plan görseli `localStorage: app_bg_image`; taslak `localStorage: proje_taslak`; ilk açılış hızı için projeler listesi `localStorage`'da cache'lenir, sonra Firebase tazele.

## 🛡️ Kritik Fonksiyonel Kurallar (Hata Önleyici)
- **Durumlar:** "Bitti", "Yarım Kaldı", "Bitmedi ama çalışıyor", "Pasif", "Arşiv". "Devam Eden" = "Yarım Kaldı" + "Bitmedi ama çalışıyor".
- **Taslak (V6):** 300ms debounce ile `localStorage: proje_taslak`. Taslak kaydı **asla** `modalKapat` içinde/sonrasında tetiklenmez.
- **Modal güvenliği:** metin seçerken mouse dışarı kayarsa modal kapanmasın — `mousedown`/`click` overlay çapraz kontrolünü bozmayın.
- **Lokal yol temizleme:** `f-lokal-yol` input'unda `paste`+`input` event'leri baş/son tırnakları temizler (Windows "Yol olarak kopyala" `"C:\yol"` formatı).
- **Hızlı IDE/Hesap ekleme:** form içi "+" butonları `hizli-ide-panel` / `hizli-hesap-panel` açar; paneller birbirini kapatır; `modalAc()` içinde her ikisi de kapatılır.
- **Auth:** Google Sign-In popup; redirect'e düşülürse `getRedirectResult()`. Çıkışta `firebase.auth().signOut()`.
- **`yukle()` throttle:** 200ms içinde tekrar çağrılırsa aynı promise paylaşılır (in-flight cache).

## 📂 Önemli Dosyalar
- `public/index.html` — tek canlı kaynak.
- `docs/archive/ide_yonetici.pyw` — arşiv masaüstü uygulaması (referans).
- `docs/archive/PRD-v3.0-uygulanmamis.md` — uygulanmamış eski plan.
- `firebase.json` — hosting + no-store header'ları + cleanUrls; `database.rules.json` — kullanıcı yalıtımı.

## 🚀 İş Akışı ve Doğrulama
1. `public/index.html` düzenle.
2. Tarayıcıda `Ctrl+F5` ile test et (header'lar `no-store` ama yine de yapın).
3. `firebase deploy --only hosting` ile yayınla.
4. Tanılama: uygulama içi Ayarlar paneli `/api/diagnostic`'i shim üzerinden yanıtlar (artık gerçek bir backend uç noktası yoktur).

## ⚠️ Bilinen "Gotcha"lar
- **Tarayıcı Cache:** `no-store` header'larına rağmen eski sürüm görünürse `Ctrl+F5`.
- **Bayat belge uyarısı:** README/agent.md dışında kalan eski commit mesajları ve `.kiro/specs` eski masaüstü/SQLite dönemini anlatır; mimariyi yorumlarken bu dosyayı referans alın.
- **Compat SDK:** `firebase.compat.js` kasıtlı; modular SDK geçişi Vite fazında yapılacak.
