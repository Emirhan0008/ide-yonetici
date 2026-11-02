// Proje ekleme/düzenleme modalı + silme onayı + taslak sistemi (V6 kurallarıyla).
// Kurallar (agent.md): taslak 300ms debounce; taslak kaydı modalKapat içinde/sonrasında
// tetiklenmez; overlay kapanışı mousedown+click çapraz kontrolüyle yapılır.
import type { Durum, IdeTuru, Proje, ProjeForm, Sahiplik } from '../model';
import { projeEkle, projeGuncelle, projeSil } from '../data/projeler';
import { gorselOku, gorseliKucult, gorselSil, gorselYaz } from '../data/gorseller';
import { $, bildirim } from './dom';
import { rastgeleRenk } from './renkler';

const TASLAK_ANAHTAR = 'proje_taslak';

interface ModalCtx {
  uid(): string | null;
}

let ctx: ModalCtx | null = null;
let duzenlemeId: string | null = null;
let taslakTimer: ReturnType<typeof setTimeout> | null = null;
let overlayTiklamaBaslangic: EventTarget | null = null;
/** Görsel kararı: null=dokunma, 'sil'=kaldır, string=yeni küçültülmüş data-url yaz. */
let gorselKarar: string | 'sil' | null = null;

const deger = (id: string): string => ($(id) as HTMLInputElement).value.trim();

function formVerisi(): ProjeForm {
  return {
    proje_adi: deger('f-proje'),
    ide_adi: deger('f-ide-adi'),
    ide_turu: (deger('f-ide-tur') || 'Bulut') as IdeTuru,
    ide_url: deger('f-url'),
    hesap_adi: deger('f-hesap'),
    hesap_email: deger('f-email'),
    durum: (deger('f-durum-sec') || 'Yarım Kaldı') as Durum,
    sahiplik: (deger('f-sahiplik-sec') || 'Bireysel') as Sahiplik,
    notlar: deger('f-notlar'),
    etiketler: deger('f-etiketler'),
    lokal_yol: deger('f-lokal-yol'),
    deploy_url: deger('f-deploy-url'),
    kart_rengi: renkKayitDegeri(),
  };
}

function setDeger(id: string, value: string): void {
  ($(`f-${id}`) as HTMLInputElement).value = value;
}

function formDoldur(p: Partial<Proje>): void {
  setDeger('proje', p.proje_adi || '');
  setDeger('ide-adi', p.ide_adi || '');
  setDeger('ide-tur', p.ide_turu || 'Bulut');
  setDeger('url', p.ide_url || '');
  setDeger('hesap', p.hesap_adi || '');
  setDeger('email', p.hesap_email || '');
  setDeger('durum-sec', p.durum || 'Yarım Kaldı');
  setDeger('sahiplik-sec', p.sahiplik || 'Bireysel');
  setDeger('notlar', p.notlar || '');
  setDeger('etiketler', p.etiketler || '');
  setDeger('lokal-yol', p.lokal_yol || '');
  setDeger('deploy-url', p.deploy_url || '');
  renkInputAyarla(p.kart_rengi || '');
}

/* ===== Renk seçici ===== */
function renkKayitDegeri(): string {
  const checkbox = $('f-kart-rengi-ozel') as HTMLInputElement;
  const input = $('f-kart-rengi-deger') as HTMLInputElement;
  return checkbox.checked ? input.value : '';
}
function renkInputAyarla(renk: string): void {
  const checkbox = $('f-kart-rengi-ozel') as HTMLInputElement;
  const input = $('f-kart-rengi-deger') as HTMLInputElement;
  checkbox.checked = !!renk;
  input.value = renk || '#0ea5e9';
  input.disabled = !renk;
}

/* ===== Görsel önizleme ===== */
function onizlemeGoster(dataUrl: string | null): void {
  const wrap = $('gorsel-onizleme-wrap');
  const kutu = $('gorsel-onizleme');
  if (dataUrl) {
    kutu.style.backgroundImage = `url('${dataUrl}')`;
    wrap.classList.add('goster');
  } else {
    kutu.style.backgroundImage = '';
    wrap.classList.remove('goster');
  }
}

/* ===== Taslak (V6) ===== */
function taslakKaydet(): void {
  if (duzenlemeId) return; // taslak yalnızca yeni proje formu için
  if (taslakTimer) clearTimeout(taslakTimer);
  taslakTimer = setTimeout(() => {
    try {
      localStorage.setItem(TASLAK_ANAHTAR, JSON.stringify(formVerisi()));
      $('draft-badge')?.classList.add('show');
    } catch { /* depolama doluysa sessiz geç */ }
  }, 300);
}

function taslakYukle(): boolean {
  try {
    const ham = localStorage.getItem(TASLAK_ANAHTAR);
    if (!ham) return false;
    const t = JSON.parse(ham) as Partial<ProjeForm>;
    if (!t || typeof t !== 'object') return false;
    formDoldur(t);
    $('draft-badge')?.classList.add('show');
    return true;
  } catch {
    return false;
  }
}

function taslakTemizle(): void {
  localStorage.removeItem(TASLAK_ANAHTAR);
  $('draft-badge')?.classList.remove('show');
}

/* ===== Modal aç/kapat ===== */
export function modalAc(proje?: Proje): void {
  if (!ctx || !ctx.uid()) {
    bildirim('Önce Google ile giriş yapın', 'err');
    return;
  }
  duzenlemeId = proje?.id ?? null;
  gorselKarar = null;
  $('modal-baslik').textContent = proje ? 'Projeyi Düzenle' : 'Yeni Proje';
  onizlemeGoster(null);

  if (proje) {
    formDoldur(proje);
    if (proje.kart_gorseli) {
      onizlemeGoster(proje.kart_gorseli); // eski format: inline
    } else {
      const uid = ctx.uid();
      const sabitId = proje.id;
      if (uid) void gorselOku(uid, sabitId).then((d) => { if (d && duzenlemeId === sabitId) onizlemeGoster(d); }).catch(() => undefined);
    }
  } else {
    formDoldur({});
    if (!taslakYukle()) $('draft-badge')?.classList.remove('show');
  }

  $('modal-overlay').classList.add('show');
  document.body.classList.add('modal-lock');
}

export function modalKapat(): void {
  // KURAL: burada taslakKaydet() YOK — taslak yalnızca yazarken otomatik kaydedilir.
  if (taslakTimer) { clearTimeout(taslakTimer); taslakTimer = null; }
  $('modal-overlay').classList.remove('show');
  document.body.classList.remove('modal-lock');
}

/* ===== Silme onayı ===== */
let silId: string | null = null;
export function silOnayAc(id: string, ad: string): void {
  silId = id;
  $('sil-proje-adi').textContent = ad;
  $('sil-overlay').classList.add('show');
}
function silKapat(): void {
  silId = null;
  $('sil-overlay').classList.remove('show');
}

/* ===== Kurulum (bir kez) ===== */
export function modalKur(baglam: ModalCtx): void {
  ctx = baglam;
  const overlay = $('modal-overlay');
  // Metin seçerken mouse dışarı kayarsa kapanmasın: mousedown+click çapraz kontrolü.
  overlay.addEventListener('mousedown', (e) => { overlayTiklamaBaslangic = e.target; });
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay && overlayTiklamaBaslangic === overlay) modalKapat();
  });
  $('modal-kapat').addEventListener('click', modalKapat);
  $('modal-iptal').addEventListener('click', modalKapat);

  const silOverlay = $('sil-overlay');
  silOverlay.addEventListener('click', (e) => { if (e.target === silOverlay) silKapat(); });
  $('sil-iptal').addEventListener('click', silKapat);
  $('sil-iptal2').addEventListener('click', silKapat);
  $('sil-onayla').addEventListener('click', async () => {
    const uid = ctx ? ctx.uid() : null;
    if (!uid || !silId) return;
    const id = silId;
    silKapat();
    await projeSil(uid, id);
    await gorselSil(uid, id).catch(() => undefined);
    bildirim('Silindi');
  });

  $('kaydet-btn').addEventListener('click', kaydet);

  // Form içi otomatik taslak + renk/görsel kontrolleri
  const govde = document.querySelector('#modal .modal-body') as HTMLElement;
  govde.addEventListener('input', (e) => {
    taslakKaydet();
    if ((e.target as HTMLElement).id === 'f-kart-rengi-deger') {
      ($('f-kart-rengi-ozel') as HTMLInputElement).checked = true;
      ($('f-kart-rengi-deger') as HTMLInputElement).disabled = false;
    }
  });
  govde.addEventListener('change', () => taslakKaydet());
  ($('f-kart-rengi-ozel') as HTMLInputElement).addEventListener('change', (e) => {
    ($('f-kart-rengi-deger') as HTMLInputElement).disabled = !(e.target as HTMLInputElement).checked;
    taslakKaydet();
  });
  $('renk-rastgele').addEventListener('click', () => {
    renkInputAyarla(rastgeleRenk());
    taslakKaydet();
  });
  $('renk-sifirla').addEventListener('click', () => {
    renkInputAyarla('');
    taslakKaydet();
  });

  $('gorsel-kaldir').addEventListener('click', () => {
    gorselKarar = 'sil';
    onizlemeGoster(null);
  });
  $('gorsel-sec-btn').addEventListener('click', () => ($('f-kart-gorseli') as HTMLInputElement).click());
  ($('f-kart-gorseli') as HTMLInputElement).addEventListener('change', async (e) => {
    const dosya = ((e.target as HTMLInputElement).files || [])[0];
    if (!dosya) return;
    if (dosya.size > 2 * 1024 * 1024) { bildirim('Görsel 2MB sınırını aşıyor', 'err'); return; }
    const okuyucu = new FileReader();
    okuyucu.onload = async () => {
      try {
        const kucuk = await gorseliKucult(String(okuyucu.result));
        gorselKarar = kucuk;
        onizlemeGoster(kucuk);
      } catch { bildirim('Görsel işlenemedi', 'err'); }
    };
    okuyucu.readAsDataURL(dosya);
    (e.target as HTMLInputElement).value = '';
  });

  // Windows "Yol olarak kopyala" tırnak temizliği (eski gotcha)
  const yol = $('f-lokal-yol');
  const temizle = (v: string) => v.trim().replace(/^["']+|["']+$/g, '');
  yol.addEventListener('paste', (e) => {
    e.preventDefault();
    const metin = (e as ClipboardEvent).clipboardData ? (e as ClipboardEvent).clipboardData!.getData('text') : '';
    (yol as HTMLInputElement).value = temizle(metin);
    taslakKaydet();
  });
  yol.addEventListener('input', () => {
    const su = (yol as HTMLInputElement).value;
    const t = temizle(su);
    if (t !== su) (yol as HTMLInputElement).value = t;
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { modalKapat(); silKapat(); }
  });
}

/* ===== Kaydet ===== */
async function kaydet(): Promise<void> {
  const uid = ctx ? ctx.uid() : null;
  if (!uid) return;
  const form = formVerisi();
  if (!form.proje_adi) { bildirim('Proje adı gerekli!', 'err'); return; }

  const btn = $('kaydet-btn') as HTMLButtonElement;
  if (btn.disabled) return; // çift tıklama koruması
  btn.disabled = true;
  const eskiMetin = btn.textContent;
  btn.textContent = '⏳ Kaydediliyor…';

  try {
    if (duzenlemeId) {
      await projeGuncelle(uid, duzenlemeId, form);
      if (gorselKarar === 'sil') await gorselSil(uid, duzenlemeId);
      else if (typeof gorselKarar === 'string') await gorselYaz(uid, duzenlemeId, gorselKarar);
      bildirim('Proje güncellendi');
    } else {
      const yeni = await projeEkle(uid, form);
      if (typeof gorselKarar === 'string') await gorselYaz(uid, yeni.id, gorselKarar);
      taslakTemizle();
      bildirim('Proje eklendi');
    }
    modalKapat();
  } catch (e) {
    console.error('[kaydet]', e);
    bildirim('Hata oluştu!', 'err');
  } finally {
    btn.disabled = false;
    btn.textContent = eskiMetin;
  }
}
