// Ayarlar paneli: IDE/hesap tanımları, JSON yedek, uygulama arka planı.
import { getState } from '../store';
import {
  hesapEkle, hesapSil, ideEkle, ideSil, tanimlilariTopluYaz,
} from '../data/tanimlilar';
import { projeleriTopluYaz } from '../data/projeler';
import { gorseliKucult, gorselleriGocEt } from '../data/gorseller';
import { $, bildirim, esc } from './dom';
import { SURUM } from '../verziyon';

interface AyarCtx {
  uid(): string | null;
}

let ctx: AyarCtx | null = null;

const BG_ANAHTAR = 'app_bg_image';
const BG_KENAR = 1280; // localStorage sınırına sığacak makimum arka plan boyutu

/* ===== Arka plan ===== */
export function arkaPlanInit(): void {
  const veri = localStorage.getItem(BG_ANAHTAR);
  const katman = $('app-bg-katman');
  if (veri) {
    katman.style.backgroundImage = `url('${veri}')`;
    katman.classList.add('aktif');
  }
}

function arkaPlanSec(dosya: File): void {
  const okuyucu = new FileReader();
  okuyucu.onload = async () => {
    try {
      const kucuk = await gorseliKucult(String(okuyucu.result), BG_KENAR);
      try {
        localStorage.setItem(BG_ANAHTAR, kucuk);
      } catch {
        bildirim('Görsel çok büyük — daha küçük dene', 'err');
        return;
      }
      const katman = $('app-bg-katman');
      katman.style.backgroundImage = `url('${kucuk}')`;
      katman.classList.add('aktif');
      bildirim('Arka plan güncellendi');
    } catch {
      bildirim('Görsel işlenemedi', 'err');
    }
  };
  okuyucu.readAsDataURL(dosya);
}

function arkaPlanKaldir(): void {
  localStorage.removeItem(BG_ANAHTAR);
  const katman = $('app-bg-katman');
  katman.classList.remove('aktif');
  katman.style.backgroundImage = '';
  bildirim('Arka plan kaldırıldı');
}

/* ===== Liste render ===== */
function listeRender(): void {
  const durum = getState();
  const ideListe = $('ayar-ide-liste');
  ideListe.innerHTML = durum.ideler.length === 0
    ? '<div class="ayar-empty">Henüz tanımlı IDE yok.</div>'
    : durum.ideler.map((i) => `
      <div class="ayar-item">
        <div class="ai-info">
          <div class="ai-name">${i.ide_turu === 'Bulut' ? '☁' : '🖥'} ${esc(i.ide_adi)}</div>
          ${i.ide_url ? `<div class="ai-detail">${esc(i.ide_url)}</div>` : ''}
        </div>
        <button class="btn-icon danger" data-sil-ide="${esc(i.id)}" title="Sil" type="button">🗑️</button>
      </div>`).join('');

  const hesapListe = $('ayar-hesap-liste');
  hesapListe.innerHTML = durum.hesaplar.length === 0
    ? '<div class="ayar-empty">Henüz tanımlı hesap yok.</div>'
    : durum.hesaplar.map((h) => `
      <div class="ayar-item">
        <div class="ai-info">
          <div class="ai-name">👤 ${esc(h.hesap_adi)}</div>
          ${h.hesap_email ? `<div class="ai-detail">${esc(h.hesap_email)}</div>` : ''}
        </div>
        <button class="btn-icon danger" data-sil-hesap="${esc(h.id)}" title="Sil" type="button">🗑️</button>
      </div>`).join('');

  $('ayar-veri-bilgi').innerHTML = durum.kullanici
    ? `Hesap: <b>${esc(durum.kullanici.email)}</b><br>` +
      `Bulutta: <b>${durum.projeler.length}</b> proje · <b>${durum.ideler.length}</b> IDE · <b>${durum.hesaplar.length}</b> hesap<br>` +
      `JSON yükleme mevcut verilerin ÜZERİNE yazar.`
    : 'Giriş yapılmamış.';

  const bilgiEl = $('ayar-veri-bilgi');
  bilgiEl.innerHTML += `<br>Sürüm: <b>v${SURUM}</b>`;
  const sonYedek = localStorage.getItem('son_yedek');
  const yedekGun = sonYedek ? Math.floor((Date.now() - Date.parse(sonYedek)) / 86400000) : null;
  if (durum.kullanici) {
    if (yedekGun === null) bilgiEl.innerHTML += '<br>💡 Henüz bu tarayıcıdan yedek indirmedin — ara sıra JSON yedek almak iyi bir alışkanlık.';
    else if (yedekGun >= 7) bilgiEl.innerHTML += `<br>⚠ Son yedekten ${yedekGun} gün geçti — bir yedek indirmenin zamanı gelmiş.`;
  }

  // Eski formatta (kart içinde 2MB'a varan base64) görsel taşıyan proje sayısı
  const gocAdedi = durum.projeler.filter((p) => !!p.kart_gorseli).length;
  const gocBilgi = $('ayar-goc-bilgi');
  const gocBtn = $('ayar-goc');
  if (gocAdedi > 0) {
    gocBilgi.style.display = '';
    gocBilgi.innerHTML = `${gocAdedi} projede <b>eski biçim</b> gömülü kart görseli var. Taşıma bunları küçültüp ayrı alana (` +
      `<code>gorseller/</code>) koyar; proje listesi hafifler, görseller tembel yüklenir.`;
    gocBtn.style.display = '';
    gocBtn.textContent = `🔄 Eski Kart Görsellerini Taşı (${gocAdedi})`;
  } else {
    gocBilgi.style.display = 'none';
    gocBtn.style.display = 'none';
  }
}

/* ===== Yedek ===== */
function disaAktar(): void {
  const d = getState();
  const veri = {
    surum: 1,
    tarih: new Date().toISOString(),
    projeler: d.projeler,
    ideler: d.ideler,
    hesaplar: d.hesaplar,
  };
  const blob = new Blob([JSON.stringify(veri, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ide-yonetici-yedek-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  localStorage.setItem('son_yedek', new Date().toISOString());
  bildirim('Yedek indirildi');
}

async function iceAktar(dosya: File): Promise<void> {
  const uid = ctx ? ctx.uid() : null;
  if (!uid) { bildirim('Önce giriş yapın', 'err'); return; }
  let veri: { projeler?: unknown[]; ideler?: unknown[]; hesaplar?: unknown[] };
  try {
    veri = JSON.parse(await dosya.text());
  } catch {
    bildirim('Geçersiz JSON dosyası', 'err');
    return;
  }
  if (!Array.isArray(veri.projeler)) {
    bildirim('Dosyada "projeler" listesi yok', 'err');
    return;
  }
  const onay = confirm(
    `Mevcut ${getState().projeler.length} projenin yerine ${veri.projeler.length} proje yüklenecek. Devam?`,
  );
  if (!onay) return;
  try {
    // Eski inline kart görselleri RTDB'ye geri yazılmaz (Faz 2 politikası).
    const projeler = (veri.projeler as Record<string, unknown>[]).map((p) => {
      const { id: _id, kart_gorseli: _g, ...temiz } = p;
      return temiz;
    });
    await projeleriTopluYaz(uid, projeler as never);
    if (Array.isArray(veri.ideler) && veri.ideler.length) await tanimlilariTopluYaz(uid, 'ideler', veri.ideler as Record<string, unknown>[]);
    if (Array.isArray(veri.hesaplar) && veri.hesaplar.length) await tanimlilariTopluYaz(uid, 'hesaplar', veri.hesaplar as Record<string, unknown>[]);
    bildirim('Veriler yüklendi');
  } catch (e) {
    console.error('[iceAktar]', e);
    bildirim('Yükleme başarısız', 'err');
  }
}

/* ===== Sekme + aç/kapat ===== */
function sekme(idx: number): void {
  document.querySelectorAll<HTMLElement>('.ayar-tab').forEach((t) => t.classList.toggle('active', Number(t.dataset.sec) === idx));
  document.querySelectorAll<HTMLElement>('.ayar-sec').forEach((s) => s.classList.toggle('active', s.dataset.sec === String(idx)));
}

export function ayarlarAc(): void {
  listeRender();
  sekme(0);
  $('ayar-overlay').classList.add('show');
  document.body.classList.add('modal-lock');
}

export function ayarlarKapat(): void {
  $('ayar-overlay').classList.remove('show');
  document.body.classList.remove('modal-lock');
}

/* ===== Kurulum ===== */
export function ayarlarKur(baglam: AyarCtx): void {
  ctx = baglam;
  const overlay = $('ayar-overlay');
  overlay.addEventListener('click', (e) => { if (e.target === overlay) ayarlarKapat(); });
  $('ayar-kapat').addEventListener('click', ayarlarKapat);
  document.querySelectorAll<HTMLElement>('.ayar-tab').forEach((t) =>
    t.addEventListener('click', () => sekme(Number(t.dataset.sec))));

  $('ayar-ide-ekle').addEventListener('click', async () => {
    const uid = ctx ? ctx.uid() : null;
    if (!uid) return;
    const ad = ($('ayar-ide-adi') as HTMLInputElement).value.trim();
    if (!ad) { bildirim('IDE adı gerekli!', 'err'); return; }
    const tur = ($('ayar-ide-turu') as HTMLSelectElement).value as 'Bulut' | 'Lokal';
    const url = ($('ayar-ide-url') as HTMLInputElement).value.trim();
    try {
      await ideEkle(uid, { ide_adi: ad, ide_turu: tur, ...(url ? { ide_url: url } : {}) });
      ($('ayar-ide-adi') as HTMLInputElement).value = '';
      ($('ayar-ide-url') as HTMLInputElement).value = '';
      bildirim('IDE eklendi');
    } catch (e) { console.error('[ayarlar] ide ekle:', e); bildirim('Kaydedilemedi', 'err'); }
  });

  $('ayar-hesap-ekle').addEventListener('click', async () => {
    const uid = ctx ? ctx.uid() : null;
    if (!uid) return;
    const ad = ($('ayar-hesap-adi') as HTMLInputElement).value.trim();
    if (!ad) { bildirim('Hesap adı gerekli!', 'err'); return; }
    const email = ($('ayar-hesap-email') as HTMLInputElement).value.trim();
    try {
      await hesapEkle(uid, { hesap_adi: ad, ...(email ? { hesap_email: email } : {}) });
      ($('ayar-hesap-adi') as HTMLInputElement).value = '';
      ($('ayar-hesap-email') as HTMLInputElement).value = '';
      bildirim('Hesap eklendi');
    } catch (e) { console.error('[ayarlar] hesap ekle:', e); bildirim('Kaydedilemedi', 'err'); }
  });

  // Liste silme butonları (delegasyon)
  $('ayar-ide-liste').addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>('[data-sil-ide]');
    const uid = ctx ? ctx.uid() : null;
    if (!btn || !uid) return;
    void ideSil(uid, btn.dataset.silIde as string).then(
      () => bildirim('IDE silindi'),
      () => bildirim('Silinemedi', 'err'),
    );
  });
  $('ayar-hesap-liste').addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>('[data-sil-hesap]');
    const uid = ctx ? ctx.uid() : null;
    if (!btn || !uid) return;
    void hesapSil(uid, btn.dataset.silHesap as string).then(
      () => bildirim('Hesap silindi'),
      () => bildirim('Silinemedi', 'err'),
    );
  });

  $('ayar-disa-aktar').addEventListener('click', disaAktar);
  $('ayar-ice-aktar-btn').addEventListener('click', () => ($('ayar-ice-aktar') as HTMLInputElement).click());
  ($('ayar-ice-aktar') as HTMLInputElement).addEventListener('change', (e) => {
    const dosya = ((e.target as HTMLInputElement).files || [])[0];
    if (dosya) void iceAktar(dosya).then(ayarlarKapat);
    (e.target as HTMLInputElement).value = '';
  });

  $('ayar-bg-sec').addEventListener('click', () => ($('ayar-bg-dosya') as HTMLInputElement).click());
  ($('ayar-bg-dosya') as HTMLInputElement).addEventListener('change', (e) => {
    const dosya = ((e.target as HTMLInputElement).files || [])[0];
    if (dosya) arkaPlanSec(dosya);
    (e.target as HTMLInputElement).value = '';
  });
  $('ayar-bg-kaldir').addEventListener('click', arkaPlanKaldir);

  // Bir defalık görsel göçü (eski inline kart_gorseli → gorseller/ yolu + küçültme)
  $('ayar-goc').addEventListener('click', async () => {
    const uid = ctx ? ctx.uid() : null;
    if (!uid) return;
    const adaylar = getState().projeler.filter((p) => !!p.kart_gorseli);
    if (adaylar.length === 0) return;
    if (!confirm(`${adaylar.length} projedeki gömülü görseller küçültülüp taşınacak. Devam?`)) return;
    const btn = $('ayar-goc') as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = '⏳ Taşınıyor…';
    try {
      const tasinan = await gorselleriGocEt(uid, adaylar);
      bildirim(`${tasinan} görsel taşındı`);
      listeRender();
    } catch (e) {
      console.error('[ayarlar] göç:', e);
      bildirim('Göç başarısız', 'err');
    } finally {
      btn.disabled = false;
    }
  });
}
