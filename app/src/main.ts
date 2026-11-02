// Uygulama girişi: auth → veri abonelikleri → filtrele/sırala → render.
import './styles/tema.css';
import './styles/kartlar.css';
import './styles/modal.css';
import './styles/ayarlar.css';
import './styles/cila.css';

import { cikisYap, authAboneOl, girisYap } from './auth';
import { gorselOku } from './data/gorseller';
import { hizliDurum as veriHizliDurum, kartRengiKaydet, projeleriDinle } from './data/projeler';
import { hesaplariDinle, ideleriDinle } from './data/tanimlilar';
import type { Durum, Proje } from './model';
import { devamEdiyorMu } from './model';
import type { AppState } from './store';
import { aboneOl, istatistikHesapla, setState } from './store';
import { $, benzersizListe, bildirim } from './ui/dom';
import { ayarlarAc, ayarlarKur, arkaPlanInit } from './ui/ayarlar';
import { renderGrid, yuklemeIskeleti } from './ui/kartlar';
import { modalAc, modalKur, silOnayAc } from './ui/modal';
import { temaDegistir, temaInit } from './ui/tema';

/* En güncel state — store aboneliğinde tazelenir; olay dinleyicileri buradan okur. */
let sonDurum: AppState | null = null;
const uid = () => sonDurum?.kullanici?.uid ?? null;

/* ===== Kurulum ===== */
temaInit();
arkaPlanInit();
modalKur({ uid });
ayarlarKur({ uid });

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
$('btn-ayarlar').addEventListener('click', ayarlarAc);
$('dd-ayarlar').addEventListener('click', () => {
  $('avatar-dd').classList.remove('is-open');
  ayarlarAc();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    $('ayar-overlay').classList.remove('show');
    if (!$('modal-overlay').classList.contains('show') && !$('sil-overlay').classList.contains('show')) {
      document.body.classList.remove('modal-lock');
    }
  }
});

/* ===== Tıklanabilir istatistikler ===== */
$('stats').addEventListener('click', (e) => {
  const stat = (e.target as HTMLElement).closest<HTMLElement>('.stat');
  if (!stat) return;
  const fDurum = $<HTMLSelectElement>('f-durum');
  const fTur = $<HTMLSelectElement>('f-tur');
  const fSahiplik = $<HTMLSelectElement>('f-sahiplik');

  const hedefDurum = stat.dataset.durum;
  const hedefTur = stat.dataset.tur;
  const hedefSahiplik = stat.dataset.sahiplik;

  if (stat.dataset.sifirla !== undefined || (!hedefDurum && !hedefTur && !hedefSahiplik)) {
    fDurum.value = ''; fTur.value = ''; fSahiplik.value = '';
  } else {
    // Toggle: aynı filtreye tekrar basınca temizle
    if (hedefDurum) fDurum.value = fDurum.value === hedefDurum ? '' : hedefDurum;
    if (hedefTur) fTur.value = fTur.value === hedefTur ? '' : hedefTur;
    if (hedefSahiplik) fSahiplik.value = fSahiplik.value === hedefSahiplik ? '' : hedefSahiplik;
  }
  if (sonDurum) render(sonDurum);
});

/* ===== Klavye kısayolları: N yeni proje, / arama ===== */
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const hedef = e.target as HTMLElement;
  const yaziMi = hedef.tagName === 'INPUT' || hedef.tagName === 'TEXTAREA' || hedef.tagName === 'SELECT' || hedef.isContentEditable;
  if (yaziMi) return;
  const panelAcik = $('modal-overlay').classList.contains('show')
    || $('ayar-overlay').classList.contains('show')
    || $('sil-overlay').classList.contains('show');
  if (panelAcik) return;
  if (e.key === 'n' || e.key === 'N') {
    e.preventDefault();
    modalAc();
  } else if (e.key === '/') {
    e.preventDefault();
    ($('ara') as HTMLInputElement).focus();
  }
});

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
  etiketSec(etiket: string): void {
    const araKutusu = $<HTMLInputElement>('ara');
    araKutusu.value = etiket;
    araKutusu.focus();
    if (sonDurum) render(sonDurum);
  },
};

/* ===== Filtre + render ===== */
(['ara', 'f-durum', 'f-tur', 'f-ide', 'f-sahiplik', 'f-sira'] as const).forEach((id) => {
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
      if (fDurum === 'devam' ? !devamEdiyorMu(p.durum) : fDurum && p.durum !== fDurum) return false;
      if (fTur && p.ide_turu !== fTur) return false;
      if (fIde && (p.ide_adi || '').toLowerCase() !== fIde) return false;
      if (fSahiplik && (p.sahiplik || 'Bireysel') !== fSahiplik) return false;
      return true;
    })
    .sort((a, b) => {
      const sira = $<HTMLSelectElement>('f-sira').value || 'guncel';
      const guncelKey = (p: Proje): string => p.guncelleme_tarihi || p.olusturma_tarihi || p.id || '';
      switch (sira) {
        case 'yeni': return (b.olusturma_tarihi || '').localeCompare(a.olusturma_tarihi || '');
        case 'eski': return (a.olusturma_tarihi || '').localeCompare(b.olusturma_tarihi || '');
        case 'az': return a.proje_adi.localeCompare(b.proje_adi, 'tr');
        case 'ide': return a.ide_adi.localeCompare(b.ide_adi, 'tr') || a.proje_adi.localeCompare(b.proje_adi, 'tr');
        default: return guncelKey(b).localeCompare(guncelKey(a));
      }
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

  // Aktif filtre eşleşen stat kartlarını işaretle
  const fDurum = $<HTMLSelectElement>('f-durum').value;
  const fTur = $<HTMLSelectElement>('f-tur').value;
  const fSahiplik = $<HTMLSelectElement>('f-sahiplik').value;
  document.querySelectorAll<HTMLElement>('#stats .stat').forEach((st) => {
    const aktif =
      (st.dataset.durum && st.dataset.durum === fDurum) ||
      (st.dataset.tur && st.dataset.tur === fTur) ||
      (st.dataset.sahiplik && st.dataset.sahiplik === fSahiplik);
    st.classList.toggle('secili', !!aktif);
  });

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
  // Yükleme durumu: oturum çözülmemişse veya giriş yapıldıysa ama liste ilk kez gelmediyse
  // asla "giriş yap" / "proje yok" gösterme — iskelet göster.
  if (!durum.oturumHazir || (durum.kullanici && !durum.veriHazir)) {
    $('sayim').textContent = '';
    kartlar.innerHTML = yuklemeIskeleti();
    return;
  }
  if (!durum.kullanici) {
    $('sayim').textContent = '';
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
  const gosterilen = kartlar.querySelectorAll('.card').length;
  $('sayim').textContent = durum.projeler.length === gosterilen
    ? `${gosterilen} proje`
    : `${gosterilen} / ${durum.projeler.length} proje gösteriliyor`;
}

/* ===== Abonelikler ===== */
let dinleyiciler: Array<() => void> = [];
let oncekiUid: string | null = null;

authAboneOl((kullanici) => {
  if (oncekiUid === kullanici?.uid) { setState({ oturumHazir: true }); return; }
  oncekiUid = kullanici?.uid ?? null;
  dinleyiciler.forEach((f) => f());
  dinleyiciler = kullanici
    ? [
        projeleriDinle(kullanici.uid, (projeler) => setState({ projeler, veriHazir: true })),
        ideleriDinle(kullanici.uid, (ideler) => setState({ ideler })),
        hesaplariDinle(kullanici.uid, (hesaplar) => setState({ hesaplar })),
      ]
    : [];
  setState({ kullanici, projeler: [], ideler: [], hesaplar: [], oturumHazir: true, veriHazir: false });
});

aboneOl((durum) => {
  const avatarDegisti = sonDurum?.kullanici?.uid !== durum.kullanici?.uid;
  sonDurum = durum;
  if (avatarDegisti) avatarGuncelle(durum);
  render(durum);
});

// Yalnızca geliştirme modunda: smoke testlerin sahte veri/enjeksiyon için kullanacağı kapı.
if (import.meta.env.DEV) {
  (window as unknown as Record<string, unknown>).__test = { setState, getState: () => sonDurum };
}
