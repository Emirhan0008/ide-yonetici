// Uygulama girişi: auth → veri abonelikleri → filtrele/sırala → render.
import './styles/tema.css';
import './styles/kartlar.css';
import './styles/modal.css';

import { cikisYap, authAboneOl, girisYap } from './auth';
import { gorselOku } from './data/gorseller';
import { hizliDurum as veriHizliDurum, kartRengiKaydet, projeleriDinle } from './data/projeler';
import { hesaplariDinle, ideleriDinle } from './data/tanimlilar';
import type { Durum, Proje } from './model';
import type { AppState } from './store';
import { aboneOl, istatistikHesapla, setState } from './store';
import { $, benzersizListe, bildirim } from './ui/dom';
import { renderGrid } from './ui/kartlar';
import { modalAc, modalKur, silOnayAc } from './ui/modal';
import { temaDegistir, temaInit } from './ui/tema';

/* En güncel state — store aboneliğinde tazelenir; olay dinleyicileri buradan okur. */
let sonDurum: AppState | null = null;
const uid = () => sonDurum?.kullanici?.uid ?? null;

/* ===== Kurulum ===== */
temaInit();
modalKur({ uid });

/* ===== Avatar / auth UI ===== */
function avatarGuncelle(durum: AppState): void {
  const btn = $('avatar-btn');
  $('avatar-dd').classList.remove('is-open');
  const u = durum.kullanici;
  if (u) {
    btn.title = u.email;
    btn.innerHTML = u.resim
      ? `<img src="${u.resim}" alt="" referrerpolicy="no-referrer">`
      : (u.email[0]?.toUpperCase() ?? '?');
    $('dd-email').textContent = u.email;
  } else {
    btn.title = 'Google ile Giriş Yap';
    btn.textContent = '?';
  }
}

$('avatar-btn').addEventListener('click', () => {
  if (!uid()) {
    void girisYap().catch((e) => bildirim('Giriş başarısız: ' + (e as Error).message, 'err'));
    return;
  }
  const dd = $('avatar-dd');
  const r = $('avatar-btn').getBoundingClientRect();
  dd.style.top = `${r.bottom + 8}px`;
  dd.style.left = `${Math.max(8, r.right - 220)}px`;
  dd.classList.toggle('is-open');
});
document.addEventListener('click', (e) => {
  if (!(e.target as HTMLElement).closest('#avatar-btn,#avatar-dd')) {
    $('avatar-dd').classList.remove('is-open');
  }
});
$('dd-cikis').addEventListener('click', () => void cikisYap());
$('btn-yeni-proje').addEventListener('click', () => modalAc());
$('btn-tema').addEventListener('click', temaDegistir);

/* ===== Kart eylemleri ===== */
const kartEylemleri = {
  duzenle(id: string): void {
    const p = sonDurum?.projeler.find((x) => x.id === id);
    if (p) modalAc(p);
  },
  silOnayla(id: string, ad: string): void {
    silOnayAc(id, ad);
  },
  hizliDurum(id: string, durum: Durum): void {
    const u = uid();
    if (!u) return;
    void veriHizliDurum(u, id, durum).then(() => bildirim(`Durum: ${durum}`));
  },
  renkKaydet(id: string, renk: string): void {
    const u = uid();
    if (u) void kartRengiKaydet(u, id, renk);
  },
  yolKopyala(yol: string): void {
    void navigator.clipboard.writeText(yol).then(
      () => bildirim('Yol panoya kopyalandı'),
      () => bildirim('Kopyalanamadı', 'err'),
    );
  },
  gorselGetir(id: string): Promise<string | null> {
    const u = uid();
    return u ? gorselOku(u, id) : Promise.resolve(null);
  },
};

/* ===== Filtre + render ===== */
(['ara', 'f-durum', 'f-tur', 'f-ide', 'f-sahiplik'] as const).forEach((id) => {
  $(id).addEventListener('input', () => sonDurum && render(sonDurum));
  $(id).addEventListener('change', () => sonDurum && render(sonDurum));
});

function filtreliListe(durum: AppState): Proje[] {
  const ara = ($<HTMLInputElement>('ara')).value.toLowerCase();
  const fDurum = $<HTMLSelectElement>('f-durum').value;
  const fTur = $<HTMLSelectElement>('f-tur').value;
  const fIde = $<HTMLSelectElement>('f-ide').value.toLowerCase();
  const fSahiplik = $<HTMLSelectElement>('f-sahiplik').value;

  return durum.projeler
    .filter((p) => {
      const metin = `${p.proje_adi} ${p.ide_adi} ${p.hesap_adi} ${p.notlar} ${p.hesap_email} ${p.sahiplik || 'Bireysel'}`.toLowerCase();
      if (ara && !metin.includes(ara)) return false;
      if (fDurum && p.durum !== fDurum) return false;
      if (fTur && p.ide_turu !== fTur) return false;
      if (fIde && (p.ide_adi || '').toLowerCase() !== fIde) return false;
      if (fSahiplik && (p.sahiplik || 'Bireysel') !== fSahiplik) return false;
      return true;
    })
    .sort((a, b) => {
      const ta = a.olusturma_tarihi || a.guncelleme_tarihi || a.id || '';
      const tb = b.olusturma_tarihi || b.guncelleme_tarihi || b.id || '';
      return ta < tb ? 1 : ta > tb ? -1 : 0;
    });
}

function render(durum: AppState): void {
  const s = istatistikHesapla(durum);
  $('s-toplam').textContent = String(s.toplam);
  $('s-aktif').textContent = String(s.aktif);
  $('s-bitti').textContent = String(s.bitti);
  $('s-bulut').textContent = String(s.bulut);
  $('s-ide').textContent = String(s.ide_sayisi);
  $('s-hesap').textContent = String(s.hesap_sayisi);
  $('s-kurumsal').textContent = String(s.kurumsal);

  const ideAdlari = benzersizListe([
    ...durum.projeler.map((p) => p.ide_adi),
    ...durum.ideler.map((i) => i.ide_adi),
  ]);
  $('dl-ide').innerHTML = ideAdlari.map((i) => `<option value="${i}">`).join('');
  const seciliIde = $<HTMLSelectElement>('f-ide').value;
  $<HTMLSelectElement>('f-ide').innerHTML =
    '<option value="">Tüm IDE\'ler</option>' +
    ideAdlari.map((i) => `<option${i === seciliIde ? ' selected' : ''}>${i}</option>`).join('');
  $('dl-hesap').innerHTML = benzersizListe([
    ...durum.projeler.map((p) => p.hesap_adi),
    ...durum.hesaplar.map((h) => h.hesap_adi),
  ]).map((h) => `<option value="${h}">`).join('');
  $('dl-email').innerHTML = benzersizListe([
    ...durum.projeler.map((p) => p.hesap_email),
    ...durum.hesaplar.map((h) => h.hesap_email || ''),
  ]).map((e) => `<option value="${e}">`).join('');

  const kartlar = $('kartlar');
  if (!durum.kullanici) {
    kartlar.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">☁️</div>
      <div class="empty-text">Projelerin Google hesabınla buluta senkronize edilir.<br>Devam etmek için giriş yap.</div>
      <button class="btn btn-primary" id="bos-giris-btn" style="margin-top:8px">Google ile Giriş Yap</button>
    </div>`;
    $('bos-giris-btn').addEventListener('click', () => {
      void girisYap().catch((e) => bildirim('Giriş başarısız: ' + (e as Error).message, 'err'));
    });
    return;
  }
  renderGrid(kartlar, filtreliListe(durum), ($<HTMLInputElement>('ara')).value.toLowerCase(), kartEylemleri);
}

/* ===== Abonelikler ===== */
let dinleyiciler: Array<() => void> = [];
let oncekiUid: string | null = null;

authAboneOl((kullanici) => {
  if (oncekiUid === kullanici?.uid) return;
  oncekiUid = kullanici?.uid ?? null;
  dinleyiciler.forEach((f) => f());
  dinleyiciler = kullanici
    ? [
        projeleriDinle(kullanici.uid, (projeler) => setState({ projeler })),
        ideleriDinle(kullanici.uid, (ideler) => setState({ ideler })),
        hesaplariDinle(kullanici.uid, (hesaplar) => setState({ hesaplar })),
      ]
    : [];
  setState({ kullanici, projeler: [], ideler: [], hesaplar: [] });
});

aboneOl((durum) => {
  const avatarDegisti = sonDurum?.kullanici?.uid !== durum.kullanici?.uid;
  sonDurum = durum;
  if (avatarDegisti) avatarGuncelle(durum);
  render(durum);
});
