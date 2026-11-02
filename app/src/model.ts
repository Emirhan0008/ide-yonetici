// Uygulamanın tek tip kaynağı. RTDB'de düz JSON olarak saklanırlar;
// `id` alanı RTDB push-key'inden türetilir (objeToArray).

export const DURUMLAR = [
  'Bitti',
  'Yarım Kaldı',
  'Bitmedi ama çalışıyor',
  'Pasif',
  'Arşiv',
] as const;
export type Durum = (typeof DURUMLAR)[number];

/** "Devam Eden" istatistiğinin tanımı (agent.md kuralı). */
export function devamEdiyorMu(durum: string): boolean {
  return durum === 'Yarım Kaldı' || durum === 'Bitmedi ama çalışıyor';
}

export const IDE_TURLERI = ['Bulut', 'Lokal'] as const;
export type IdeTuru = (typeof IDE_TURLERI)[number];

export const SAHIPLIKLER = ['Bireysel', 'Kurumsal'] as const;
export type Sahiplik = (typeof SAHIPLIKLER)[number];

export interface Proje {
  id: string;
  proje_adi: string;
  ide_adi: string;
  ide_turu: IdeTuru;
  ide_url: string;
  hesap_adi: string;
  hesap_email: string;
  durum: Durum;
  sahiplik: Sahiplik;
  notlar: string;
  etiketler: string;
  lokal_yol: string;
  deploy_url: string;
  kart_rengi: string;
  /** Eski dönem: base64 data-url RTDB'de duruyordu. Faz 2'de gorseller/ yoluna taşınacak. */
  kart_gorseli?: string;
  olusturma_tarihi?: string;
  guncelleme_tarihi?: string;
}

/** Formdan gelen, id/tarihleri henüz olmayan veri. */
export type ProjeForm = Omit<Proje, 'id' | 'olusturma_tarihi' | 'guncelleme_tarihi'>;

export interface TanimliIde {
  id: string;
  ide_adi: string;
  ide_turu: IdeTuru;
  ide_url?: string;
}

export interface TanimliHesap {
  id: string;
  hesap_adi: string;
  hesap_email?: string;
}

export interface KullaniciProfili {
  uid: string;
  email: string;
  ad: string;
  resim: string;
}

export interface Istatistikler {
  toplam: number;
  aktif: number;
  bitti: number;
  bulut: number;
  kurumsal: number;
  ide_sayisi: number;
  hesap_sayisi: number;
}
