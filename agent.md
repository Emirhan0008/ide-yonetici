# 🤖 Yapay Zeka & Geliştirici Bilgi Merkezi (agent.md)

Bu dosya, projeyi devralacak olan yazılımcı veya yapay zeka ajanı için kritik teknik hafızayı ve operasyonel kuralları içerir. **Lütfen geliştirmeye başlamadan önce okuyun.**

## 🎯 Proje Vizyonu ve Durumu
Bu araç, çoklu bulut IDE (Cursor, Replit vb.) kullanımından doğan "hangi proje hangi hesapta/IDE'de kaldı?" karmaşasını çözen minimalist bir yönetim panelidir. Şu an **V3 (Vite + TypeScript)** aşamasındadır; canlı: `https://ideyonetici.web.app`.

## 🛠️ Teknik Mimari (GÜNCEL)
- **CANLI KAYNAK:** `app/` — Vite + vanilla TypeScript, modüler (framework yok).
  - `src/data/` → **TEK veri kapısı**: RTDB okuma/yazma yalnızca burada (`projeler.ts`, `tanimlilar.ts`, `gorseller.ts`, `rtdb.ts`). UI asla doğrudan Firebase çağırmaz.
  - `src/ui/` → özellik modülleri: `kartlar` (data-* delegasyonu — inline onclick YOK), `modal`, `ayarlar`, `tema`, `renkler`, `dom`.
  - `src/model.ts` → alan tipleri + durum kuralları (`devamEdiyorMu` tek kaynak). `src/store.ts` → tipli state (setState/aboneOl).
  - `src/styles/` → tema/kartlar/modal/ayarlar/cila CSS modülleri.
- **Firebase SDK:** modular v13 (npm, `firebase/app|auth|database`) — eski compat/CDN dönemi bitti.
- **BACKEND YOK.** Eski shim (`/api/...` taklidi) ÖLDÜ; `/api` diye bir şey yok. Auth: `signInWithPopup(GoogleAuthProvider)`, popup engellenirse redirect fallback.
- **Build/Deploy:** `cd app && npm run build` → `app/dist` (firebase.json oradan yayınlar) → `firebase deploy --only hosting`.
- **Cache stratejisi:** HTML `no-store`; hash'li `/assets/*` 1 yıl `immutable`. **`Ctrl+F5` ritüeli tarihe karıştı** — güncellemede yalnızca değişen dosya iner.

## 🗄️ Veri Katmanı (Firebase RTDB)
- Kök: `users/$uid/` (rules: yalnızca kendi uid'sini okur/yazar — `database.rules.json`).
- Alt yollar: `projeler/`, `ideler/`, `hesaplar/`, `gorseller/$projeId`.
  - Liste yolları RTDB push-key'li nesne dizisidir; `objeToArray()` diziye çevirir, `id` key'den gelir.
  - Abonelikler `onValue` ile gerçek zamanlı; ilk senkronda UI otomatik dolar.
- Proje alanları: `proje_adi, ide_adi, ide_turu, ide_url, hesap_adi, hesap_email, durum, sahiplik, notlar, etiketler, lokal_yol, deploy_url, kart_rengi, olusturma_tarihi, guncelleme_tarihi` (+ eski kayıtlarda miras `kart_gorseli`).
  - **Görsel politikası (Faz 2):** yeni görseller 800px JPEG'e küçültülüp AYRI `gorseller/$projeId` yoluna yazılır; kartlar tembel yükler. Eski inline `kart_gorseli` (2MB'a kadar) yalnızca miras veride vardır ve render edilir; **Ayarlar → Veri → "Eski Kart Görsellerini Taşı"** ile hepsi taşınır (`gorselleriGocEt`).
  - `kart_rengi`: boşsa duruma göre otomatik renk.
- localStorage anahtarları: `proje_taslak` (taslak), `app_tema` (tema), `app_bg_image` (uygulama arka planı, 1280px JPEG).

## 🛡️ Kritik Fonksiyonel Kurallar (Hata Önleyici)
- **Durumlar:** "Bitti", "Yarım Kaldı", "Bitmedi ama çalışıyor", "Pasif", "Arşiv". "Devam Eden" = `model.devmEdiyorMu()` — başka yerde kural yazmayın. Filtre kutusunda sihirli değer `"devam"`.
- **Taslak (V6):** 300ms debounce ile `localStorage: proje_taslak`; yalnızca YENİ proje formunda; taslak kaydı **asla** `modalKapat` içinde/sonrasında tetiklenmez.
- **Modal güvenliği:** overlay kapanışı `mousedown`+`click` çapraz kontrolüyle (metin seçerken mouse dışarı kayarsa kapanmaz) — `modal.ts`/`ayarlar.ts` kalıbını bozmayın.
- **Kart olayları:** HTML üretiminde kullanıcı verisi JS string'e GÖMÜLMEZ; `data-eylem` + delegasyon kullanılır (tırnak/XSS sınıfı hatalar böyle önlendi).
- **Lokal yol temizleme:** `f-lokal-yol` paste/input tırnak temizliği (Windows "Yol olarak kopyala").
- **TypeScript 7 notu:** `tsconfig` `erasableSyntaxOnly` açık — `<Tip>x` cast'leri YASAK, `x as Tip` kullanın.
- **Test kancası:** yalnızca DEV modda `window.__test = { setState, ... }`; e2e testleri sahte oturumu bununla kurar (gerçek Google login headless test edilemez).

## 📂 Önemli Dosyalar
- `app/` — canlı uygulama (`e2e/smoke.spec.ts` dahil; `npm test` ile koşar, dev sunucusunu kendi ayağa kaldırır).
- `docs/archive/index-v2.5-tek-dosya.html` — geçiş öncesi tek dosya sürüm (referans/geri dönüş).
- `docs/archive/ide_yonetici.pyw` — arşiv masaüstü uygulaması. `docs/archive/PRD-v3.0-uygulanmamis.md` — uygulanmamış eski plan.
- `firebase.json` — hosting `app/dist` + cache header'ları + cleanUrls; `database.rules.json` — kullanıcı yalıtımı.

## 🚀 İş Akışı ve Doğrulama
1. `cd app && npm run dev` → http://localhost:5199 (HMR).
2. Değişiklik yap; `npm test` (8 duman senaryosu) + `npm run build` (tsc tip kontrolü build'in parçası).
3. Repo kökünden `firebase deploy --only hosting`.
4. Canlıyı doğrula: `Invoke-WebRequest https://ideyonetici.web.app` → 200 + asset'ler `immutable`.

## ⚠️ Bilinen "Gotcha"lar
- **Gerçek giriş testi yalnızca elle yapılabilir** (Google popup); e2e testler DEV kancasıyla sahte oturum kurar.
- **npm argüman geçirme:** `npm run dev -- --port X` bozulabiliyor; port `vite.config.ts` içinde sabit (5199).
- **Bayat belge uyarısı:** eski commit mesajları ve `.kiro/specs` eski masaüstü/SQLite/shim dönemini anlatır; mimari için tek kaynak bu dosyadır.
- **Geri dönüş:** bir sorun olursa `firebase.json` public'i `docs/archive/index-v2.5-tek-dosya.html` içeren bir klasöre çevirip deploy etmek yeterli (RTDB şeması birebir uyumlu).

## 🗺️ Kalan İşler (öneri sırası)
1. Gerçek veriyle uzun kullanım → gerekirse hedefli DOM güncelleme (şu an tam yeniden-çizim; <100 projede sorun değil).
2. Kart üzerinde tam durum seçici (bugün yalnız Arşiv↔Bitti hızlı geçişi var; durum değişikliğinin çoğu modal üzerinden).
3. Kanban sürükle-bırak (eski sitede yarım kalmıştı) — istenirse `kartlar.ts` içine eklenir.
