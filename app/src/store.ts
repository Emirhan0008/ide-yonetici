// Minimal tipli durum deposu — eski `App` global objesinin yerine geçer.
// UI modülleri state'e doğrudan yazmaz: data/ katmanı setState ile günceller,
// UI abonelik ile yeniden çizer.
import { devamEdiyorMu } from './model';
import type { Istatistikler, KullaniciProfili, Proje, TanimliHesap, TanimliIde } from './model';

export interface AppState {
  kullanici: KullaniciProfili | null;
  /** onAuthStateChanged ilk kez döndi (oturum çözüldü; giriş kapısı ancak o zaman gösterilir). */
  oturumHazir: boolean;
  /** Giriş yapılan hesabın proje listesi ilk kez RTDB'den geldi ("proje yok" ancak o zaman gösterilir). */
  veriHazir: boolean;
  projeler: Proje[];
  ideler: TanimliIde[];
  hesaplar: TanimliHesap[];
  /** Son tam yeniden çizim zamanı (telemetri/test amaçlı). */
  sonTazeleme: number;
}

type Dinleyici = (durum: AppState) => void;

let durum: AppState = {
  kullanici: null,
  oturumHazir: false,
  veriHazir: false,
  projeler: [],
  ideler: [],
  hesaplar: [],
  sonTazeleme: 0,
};

const dinleyiciler = new Set<Dinleyici>();

export function getState(): AppState {
  return durum;
}

export function setState(parsiyel: Partial<AppState>): void {
  durum = { ...durum, ...parsiyel, sonTazeleme: Date.now() };
  dinleyiciler.forEach((d) => d(durum));
}

/** Abone ol; ilk çağrıda anında mevcut durumla tetiklenir. Unsubscribe döner. */
export function aboneOl(dinleyici: Dinleyici): () => void {
  dinleyiciler.add(dinleyici);
  dinleyici(durum);
  return () => dinleyiciler.delete(dinleyici);
}

/** "Devam Eden" tanımı model.devmEdiyorMu ile aynı kaynaktan gelir (agent.md kuralı). */
export function istatistikHesapla(d: AppState): Istatistikler {
  return {
    toplam: d.projeler.length,
    aktif: d.projeler.filter((p) => devamEdiyorMu(p.durum)).length,
    bitti: d.projeler.filter((p) => p.durum === 'Bitti').length,
    bulut: d.projeler.filter((p) => p.ide_turu === 'Bulut').length,
    kurumsal: d.projeler.filter((p) => (p.sahiplik || 'Bireysel') === 'Kurumsal').length,
    ide_sayisi: d.ideler.length,
    hesap_sayisi: d.hesaplar.length,
  };
}
