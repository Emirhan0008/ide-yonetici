// Uygulama girişi (Faz 1 iskeleti).
// Eski index.html'in tamamı Faz 3'te ui/ modüllerine taşınacak; burada sadece
// boru hattının canlı kanıtı var: auth → gerçek zamanlı veri → store → DOM.
import { authAboneOl, cikisYap, girisYap } from './auth';
import { ideleriDinle, hesaplariDinle } from './data/tanimlilar';
import { projeleriDinle } from './data/projeler';
import { aboneOl, istatistikHesapla, setState } from './store';

function $<T extends HTMLElement = HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

function baglantiLisansla(uid: string): Array<() => void> {
  return [
    projeleriDinle(uid, (projeler) => setState({ projeler })),
    ideleriDinle(uid, (ideler) => setState({ ideler })),
    hesaplariDinle(uid, (hesaplar) => setState({ hesaplar })),
  ];
}

let iptaller: Array<() => void> = [];

authAboneOl((kullanici) => {
  iptaller.forEach((f) => f());
  iptaller = kullanici ? baglantiLisansla(kullanici.uid) : [];
  setState({ kullanici, projeler: [], ideler: [], hesaplar: [] });
});

aboneOl((durum) => {
  const durumEl = $('durum');
  const girisBtn = $('giris-btn');
  const cikisBtn = $('cikis-btn');
  const ozetEl = $('ozet');

  if (durum.kullanici) {
    durumEl.textContent = `☁️ ${durum.kullanici.email}`;
    girisBtn.hidden = true;
    cikisBtn.hidden = false;
    const s = istatistikHesapla(durum);
    ozetEl.textContent =
      `${s.toplam} proje · devam eden ${s.aktif} · bitti ${s.bitti} · ` +
      `bulut ${s.bulut} · kurumsal ${s.kurumsal} · ${s.ide_sayisi} IDE · ${s.hesap_sayisi} hesap`;
  } else {
    durumEl.textContent = 'Giriş bekleniyor…';
    girisBtn.hidden = false;
    cikisBtn.hidden = true;
    ozetEl.textContent = '';
  }
});

$('giris-btn').addEventListener('click', () => {
  girisYap().catch((e) => console.error('[auth] giriş:', e));
});
$('cikis-btn').addEventListener('click', () => {
  cikisYap().catch((e) => console.error('[auth] çıkış:', e));
});
