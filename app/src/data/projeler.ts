// Projeler için tek veri kapısı. UI başka hiçbir yerden RTDB okuyup yazmaz.
import { push, ref, remove, set, update } from 'firebase/database';
import { db, kullaniciYolu } from '../firebase';
import type { Durum, Proje, ProjeForm } from '../model';
import { kullaniciDinle } from './rtdb';

/** users/$uid/projeler — ilk senkron ve sonrasındaki her değişiklik. */
export function projeleriDinle(uid: string, callback: (p: Proje[]) => void): () => void {
  return kullaniciDinle<Proje>(uid, 'projeler', callback);
}

export async function projeEkle(uid: string, form: ProjeForm): Promise<Proje> {
  const r = ref(db, kullaniciYolu(uid, 'projeler'));
  const yeniRef = await push(r, { ...form, olusturma_tarihi: new Date().toISOString() });
  if (!yeniRef.key) throw new Error('RTDB anahtarı üretilemedi');
  return { ...form, id: yeniRef.key };
}

export async function projeGuncelle(uid: string, id: string, form: ProjeForm): Promise<void> {
  const r = ref(db, kullaniciYolu(uid, `projeler/${id}`));
  await update(r, { ...form, guncelleme_tarihi: new Date().toISOString() });
}

export async function projeSil(uid: string, id: string): Promise<void> {
  await remove(ref(db, kullaniciYolu(uid, `projeler/${id}`)));
}

/** Silme-geri-alma: silinen kaydı kendi anahtarına geri yazar (id korunur). */
export async function projeGeriYukle(uid: string, id: string, veri: Omit<Proje, 'id'>): Promise<void> {
  await set(ref(db, kullaniciYolu(uid, `projeler/${id}`)), veri);
}

/** Kart üstündeki hızlı durum değiştirme — tek alan yazar. */
export async function hizliDurum(uid: string, id: string, durum: Durum): Promise<void> {
  await update(ref(db, kullaniciYolu(uid, `projeler/${id}`)), {
    durum,
    guncelleme_tarihi: new Date().toISOString(),
  });
}

/** Kart rengi — kart üzerinden anında kayıt (eski kartRengiUygula). */
export async function kartRengiKaydet(uid: string, id: string, renk: string): Promise<void> {
  await update(ref(db, kullaniciYolu(uid, `projeler/${id}`)), {
    kart_rengi: renk,
    guncelleme_tarihi: new Date().toISOString(),
  });
}

/** JSON içe aktarma: mevcut verinin yerine toplu yazım (atomik set). */
export async function projeleriTopluYaz(uid: string, projeler: ProjeForm[]): Promise<void> {
  const taban = Date.now().toString(36);
  const ob: Record<string, ProjeForm & { olusturma_tarihi: string }> = {};
  projeler.forEach((p, i) => {
    ob[`${taban}${i}`] = { ...p, olusturma_tarihi: new Date().toISOString() };
  });
  await set(ref(db, kullaniciYolu(uid, 'projeler')), ob);
}
