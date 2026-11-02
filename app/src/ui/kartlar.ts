// Kart ızgarası: HTML üretimi + olay delegasyonu.
// Eski sürümdeki inline onclick YOK — kullanıcı verisi JS string'e asla gömülmez,
// hepsi data-* üzerinden delegasyonla çalışır (tırnak/XSS sınıfı hata imkânsız).
import type { Durum, Proje } from '../model';
import { RENK_PALETI } from './renkler';
import { esc, getIdeIcon, highlight } from './dom';

export interface KartEylemleri {
  duzenle(id: string): void;
  silOnayla(id: string, ad: string): void;
  hizliDurum(id: string, durum: Durum): void;
  renkKaydet(id: string, renk: string): void;
  yolKopyala(yol: string): void;
  /** Faz 2: yeni görsel yolu. Eski kayıtlarda inline kart_gorseli olduğundan opsiyonel. */
  gorselGetir?(id: string): Promise<string | null>;
  /** Etiket çipine tıklama — o etiketi aratır (main.ts uygular). */
  etiketSec?(etiket: string): void;
  /** Kart seçimi değişti (toplu işlem; main.ts seçim durumunu tutar). */
  kartSec?(id: string, secili: boolean): void;
}

const DURUM_CLASS: Record<string, string> = {
  'Bitti': 'tag-bitti', 'Yarım Kaldı': 'tag-yarim', 'Bitmedi ama çalışıyor': 'tag-calisiyor',
  'Pasif': 'tag-pasif', 'Arşiv': 'tag-arsiv',
};
const DURUM_KISALT: Record<string, string> = {
  'Bitti': '✓ Bitti', 'Yarım Kaldı': '⏸ Yarım', 'Bitmedi ama çalışıyor': '⚙ Çalışıyor',
  'Pasif': '⏸ Pasif', 'Arşiv': '📦 Arşiv',
};
const DURUM_RENK: Record<string, string> = {
  'Bitti': '#10b981', 'Yarım Kaldı': '#f97316', 'Bitmedi ama çalışıyor': '#3b82f6',
  'Pasif': '#4a546a', 'Arşiv': '#f59e0b',
};
const DURUM_SECENEKLERI: Durum[] = ['Bitti', 'Yarım Kaldı', 'Bitmedi ama çalışıyor', 'Pasif', 'Arşiv'];

function kartHTML(p: Proje, ara: string): string {
  const durumClass = DURUM_CLASS[p.durum || ''] || 'tag-pasif';
  const durumGosterim = DURUM_KISALT[p.durum || ''] || p.durum;
  const renk = p.kart_rengi || DURUM_RENK[p.durum || ''] || '#4a546a';

  const sah = p.sahiplik || 'Bireysel';
  const sahRozet = sah === 'Kurumsal'
    ? `<span class="tag" style="background:rgba(168,85,247,.15);color:#c084fc;border:1px solid rgba(168,85,247,.35)" title="Kurumsal">🏢 Kurumsal</span>`
    : `<span class="tag" style="background:rgba(255,255,255,.04);color:var(--text2);border:1px solid var(--border)" title="Bireysel">👤 Bireysel</span>`;

  const etiketler = p.etiketler
    ? `<div class="kart-etiketler">${p.etiketler.split(',').map((e) => `<span class="tag tag-custom" data-eylem="etiket" data-etiket="${esc(e.trim())}" title="Bu etiketi ara">#${highlight(e.trim(), ara)}</span>`).join('')}</div>`
    : '';

  const acBtn = p.ide_turu === 'Bulut'
    ? (p.ide_url ? `<button class="btn btn-primary btn-sm" data-eylem="link" data-url="${esc(p.ide_url)}" title="IDE'yi aç">🚀</button>` : '')
    : (p.lokal_yol ? `<button class="btn btn-primary btn-sm" data-eylem="yol-kopyala" data-yol="${esc(p.lokal_yol)}" title="Yolu kopyala">💻</button>` : '');
  const deployBtn = p.deploy_url
    ? `<button class="btn btn-success btn-sm" data-eylem="link" data-url="${esc(p.deploy_url)}" title="Deploy edilen siteyi aç">🌐</button>`
    : '';

  const gorselDiv = p.kart_gorseli
    ? `<div class="kart-bg-gorsel" style="background-image:url('${esc(p.kart_gorseli)}')"></div>`
    : `<div class="kart-bg-gorsel" data-gorsel-yukle="${esc(p.id)}"></div>`;

  const paletHTML = RENK_PALETI.map((r) =>
    `<button class="kart-renk-popup-btn ${r === (p.kart_rengi || '') ? 'aktif' : ''}" style="background:${r}" title="${r}" data-eylem="renk-sec" data-renk="${r}" type="button"></button>`
  ).join('');

  const NOT_LIMIT = 120;
  let notHTML = '';
  if (p.notlar) {
    const uzun = p.notlar.length > NOT_LIMIT;
    notHTML = `
      <div class="card-note">${highlight(p.notlar, ara)}</div>
      ${uzun ? `<button class="devamini-oku" data-eylem="not-toggle" type="button">▾ devamını oku</button>` : ''}`;
  }

  const tarih = (p.guncelleme_tarihi || p.olusturma_tarihi || '').slice(0, 10);

  return `
    <div class="card${p.kart_gorseli ? ' has-bg' : ''}" data-kart="${esc(p.id)}" style="--kart-renk:${esc(renk)};border:2px solid ${esc(renk)}">
      ${gorselDiv}
      <div class="kart-overlay-ust"></div>
      <div class="kart-overlay-alt"></div>
      <div class="kart-renk-popup">
        <div class="kart-renk-popup-palet">${paletHTML}</div>
        <div class="kart-renk-popup-alt">
          <input type="color" value="${esc(p.kart_rengi || '#0ea5e9')}" title="Özel renk" data-eylem="renk-ozel">
          <button class="kart-renk-popup-sifirla" data-eylem="renk-sifirla" type="button">↺ Otomatik</button>
        </div>
      </div>
      <div class="card-actions-bar">
        <label class="kart-sec-kutusu" title="Toplu işlem için seç"><input type="checkbox" data-eylem="kart-sec"></label>
        ${acBtn}
        ${deployBtn}
        <select class="kart-durum-sel" data-eylem="durum-sec" title="Durumu değiştir" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:11px;padding:3px 4px;cursor:pointer;width:auto">${DURUM_SECENEKLERI.map((d) => `<option value="${esc(d)}"${d === p.durum ? ' selected' : ''}>${esc(DURUM_KISALT[d] || d)}</option>`).join('')}</select>
        <button class="btn-icon edit" data-eylem="duzenle" title="Düzenle">✏️</button>
        <button class="btn-icon danger" data-eylem="sil" title="Projeyi sil">🗑️</button>
      </div>
      <div class="card-content">
        <div class="card-title">${highlight(p.proje_adi, ara)}</div>
        ${etiketler}
        <div class="card-body">
          <div class="card-row">
            <span class="icon">${getIdeIcon(p.ide_adi)}</span>
            <span class="value" title="${esc(p.ide_adi)}">${highlight(p.ide_adi, ara)} <span class="tag ${p.ide_turu === 'Bulut' ? 'tag-bulut' : 'tag-lokal'}">${p.ide_turu === 'Bulut' ? '☁' : '🖥'}</span></span>
          </div>
          ${p.hesap_adi ? `<div class="card-row"><span class="icon">👤</span><span class="value" title="${esc(p.hesap_adi)}">${highlight(p.hesap_adi, ara)}</span></div>` : ''}
          ${notHTML}
        </div>
        <div class="card-footer">
          <span class="tag ${durumClass}" title="${esc(p.durum)}">${esc(durumGosterim)}</span>
          ${sahRozet}
          <span class="card-date">🕐 ${esc(tarih)}</span>
        </div>
      </div>
      <button class="kart-renk-btn" style="background:${esc(p.kart_rengi || 'rgba(128,128,128,0.35)')}" title="Renk değiştir" data-eylem="renk-popup" type="button"></button>
    </div>`;
}

const dinlenenler = new WeakMap<HTMLElement, KartEylemleri>();
/** Son basılan kart HTML'lerinin önbelleği (id → html) — hedefli güncelleme için. */
const kartOnbellek = new WeakMap<HTMLElement, Map<string, string>>();
/** Yüklenmiş kart görselleri (id → data-url): yeniden çizimlerde RTDB'ye tekrar gidilmez. */
const gorselCache = new Map<string, string>();

/** Oturum/veri beklenirken gösterilen parıltılı kart iskeleti (boş durumları gizler). */
export function yuklemeIskeleti(adet = 8): string {
  const kart = '<div class="card iskelet"><div class="sk sk-gorsel"></div><div class="sk-icerik"><div class="sk sk-baslik"></div><div class="sk sk-satir"></div><div class="sk sk-satir kisa"></div></div></div>';
  return '<div class="iskelet-not" style="grid-column:1/-1">⏳ Projelerin geliyor…</div>' + kart.repeat(adet);
}

export function renderGrid(
  konteyner: HTMLElement,
  liste: Proje[],
  ara: string,
  eylemler: KartEylemleri,
): void {
  if (liste.length === 0) {
    konteyner.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">🔍</div>
      <div class="empty-text">Gösterilecek proje yok.</div>
    </div>`;
    kartOnbellek.set(konteyner, new Map());
  } else {
    // Hedefli güncelleme: HTML'i değişmemiş kartların DOM düğümü yerinde korunur.
    const oncekiler = kartOnbellek.get(konteyner) ?? new Map<string, string>();
    const mevcut = new Map<string, HTMLElement>();
    konteyner.querySelectorAll<HTMLElement>(':scope > [data-kart]').forEach((el) => {
      const kartId = el.dataset.kart ?? '';
      if (!mevcut.has(kartId)) mevcut.set(kartId, el);
    });
    const sonraki = new Map<string, string>();
    const fragman = document.createDocumentFragment();
    for (const p of liste) {
      const html = kartHTML(p, ara);
      sonraki.set(p.id, html);
      const eski = mevcut.get(p.id);
      if (eski && oncekiler.get(p.id) === html) {
        fragman.appendChild(eski); // düğüm aynen taşınır: titreme/odak kaybı yok
      } else {
        const sablon = document.createElement('template');
        sablon.innerHTML = html.trim();
        fragman.appendChild(sablon.content.firstElementChild as HTMLElement);
      }
      mevcut.delete(p.id);
    }
    konteyner.textContent = ''; // süzgeç dışı kalanlar + boş-durum düğümü silinir
    konteyner.appendChild(fragman);
    kartOnbellek.set(konteyner, sonraki);
  }

  // Delegasyonu yalnızca ilk render'da bağla; eylem güncellemeleri WeakMap'ten okunur.
  dinlenenler.set(konteyner, eylemler);
  if (!konteyner.dataset.delegeEdildi) {
    konteyner.dataset.delegeEdildi = '1';
    konteyner.addEventListener('click', (e) => tiklama(konteyner, e));
    konteyner.addEventListener('change', (e) => degisim(konteyner, e));
    document.addEventListener('click', (e) => {
      const hedef = e.target as HTMLElement;
      if (!hedef.closest('[data-eylem^="renk"]') && !hedef.closest('.kart-renk-popup')) {
        konteyner.querySelectorAll('.kart-renk-popup.goster').forEach((p) => p.classList.remove('goster'));
      }
    });
  }

  // Tembel görsel yükleme (Faz 2 yolu) — yalnızca eski formatı olmayan kartlar.
  if (eylemler.gorselGetir) {
    konteyner.querySelectorAll<HTMLElement>('[data-gorsel-yukle]').forEach((el) => {
      const id = el.dataset.gorselYukle as string;
      delete el.dataset.gorselYukle; // aynı düğüm için ikinci kez istek atılmaz
      const uygula = (data: string): void => {
        el.style.backgroundImage = `url('${data}')`;
        el.closest('.card')?.classList.add('has-bg');
      };
      const onbellek = gorselCache.get(id);
      if (onbellek) {
        uygula(onbellek);
        return;
      }
      eylemler.gorselGetir?.(id).then((data) => {
        if (!data) return;
        gorselCache.set(id, data);
        uygula(data);
      }).catch(() => undefined);
    });
  }
}

function tiklama(konteyner: HTMLElement, e: MouseEvent): void {
  const eylemler = dinlenenler.get(konteyner);
  if (!eylemler) return;
  const hedef = (e.target as HTMLElement).closest<HTMLElement>('[data-eylem]');
  if (!hedef) return;
  const kart = hedef.closest<HTMLElement>('[data-kart]');
  const id = kart?.dataset.kart ?? '';
  const eylem = hedef.dataset.eylem as string;

  switch (eylem) {
    case 'link':
      window.open(hedef.dataset.url ?? '', '_blank');
      break;
    case 'yol-kopyala':
      eylemler.yolKopyala(hedef.dataset.yol ?? '');
      break;

    case 'etiket':
      eylemler.etiketSec?.(hedef.dataset.etiket ?? '');
      break;
    case 'duzenle':
      eylemler.duzenle(id);
      break;
    case 'sil': {
      const ad = kart?.querySelector('.card-title')?.textContent ?? '';
      eylemler.silOnayla(id, ad);
      break;
    }
    case 'not-toggle': {
      const notEl = hedef.previousElementSibling;
      if (notEl) {
        const acik = notEl.classList.toggle('acik');
        hedef.textContent = acik ? '▴ kapat' : '▾ devamını oku';
        if (kart) {
          kart.style.height = acik ? 'auto' : '';
          kart.style.zIndex = acik ? '2' : '';
        }
      }
      break;
    }
    case 'renk-popup':
      hedef.closest('.card')?.querySelector('.kart-renk-popup')?.classList.toggle('goster');
      break;
    case 'renk-sec':
      eylemler.renkKaydet(id, hedef.dataset.renk ?? '');
      hedef.closest('.kart-renk-popup')?.classList.remove('goster');
      break;
    case 'renk-sifirla':
      eylemler.renkKaydet(id, '');
      hedef.closest('.kart-renk-popup')?.classList.remove('goster');
      break;
  }
}

function degisim(konteyner: HTMLElement, e: Event): void {
  const eylemler = dinlenenler.get(konteyner);
  if (!eylemler) return;
  const secim = (e.target as HTMLElement).closest<HTMLElement>('[data-eylem="kart-sec"]');
  if (secim) {
    const kartEl = secim.closest<HTMLElement>('[data-kart]');
    eylemler.kartSec?.(kartEl?.dataset.kart ?? '', (e.target as HTMLInputElement).checked);
    return;
  }
  const hedef = (e.target as HTMLElement).closest<HTMLElement>('[data-eylem="durum-sec"]');
  if (hedef) {
    const id = hedef.closest<HTMLElement>('[data-kart]')?.dataset.kart ?? '';
    eylemler.hizliDurum(id, (hedef as HTMLSelectElement).value as Durum);
    return;
  }
  const renk = (e.target as HTMLElement).closest<HTMLElement>('[data-eylem="renk-ozel"]');
  if (!renk) return;
  const kart = renk.closest<HTMLElement>('[data-kart]');
  eylemler.renkKaydet(kart?.dataset.kart ?? '', (renk as HTMLInputElement).value);
  renk.closest('.kart-renk-popup')?.classList.remove('goster');
}
