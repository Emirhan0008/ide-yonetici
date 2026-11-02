// Kart görselleri — Faz 2 boru hattı.
// Eski dönem: 2MB'a varan base64 doğrudan proje nesnesinin içinde RTDB'ye yazılıyordu.
// Yeni dönem: görsel istemcide küçültülür ve AYRI bir yola (users/$uid/gorseller/$projeId)
// konur; proje listesi artık görsel taşımadan indirilir, görsel kart görünürken tembel
// yüklenir.
import { get, ref, remove, set, update } from 'firebase/database';
import { db, kullaniciYolu } from '../firebase';

const MAKS_KENAR = 800; // px — kart arka planı + blur(8px) için fazlasıyla yeterli
const JPEG_KALITE = 0.82;

export interface GorselKaydi {
  data: string; // küçültülmüş JPEG data-url
  guncelleme_tarihi: string;
}

/** data-url/PNG/JPEG girer, en fazla MAKS_KENAR kenarlı JPEG data-url çıkar. */
export function gorseliKucult(dataUrl: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onerror = () => reject(new Error('Görsel çözümlenemedi'));
    img.onload = () => {
      const oran = Math.min(1, MAKS_KENAR / Math.max(img.width, img.height));
      const w = Math.max(1, Math.round(img.width * oran));
      const h = Math.max(1, Math.round(img.height * oran));
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('canvas 2d bağlamı alınamadı'));
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL('image/jpeg', JPEG_KALITE));
    };
    img.src = dataUrl;
  });
}

export async function gorselYaz(uid: string, projeId: string, kucukDataUrl: string): Promise<void> {
  const kayit: GorselKaydi = { data: kucukDataUrl, guncelleme_tarihi: new Date().toISOString() };
  await set(ref(db, kullaniciYolu(uid, `gorseller/${projeId}`)), kayit);
}

/** Tembel yükleme: kart görünür olduğunda çağrılır. Yoksa null. */
export async function gorselOku(uid: string, projeId: string): Promise<string | null> {
  const snap = await get(ref(db, kullaniciYolu(uid, `gorseller/${projeId}`)));
  const v = snap.val() as GorselKaydi | null;
  return v?.data ?? null;
}

export async function gorselSil(uid: string, projeId: string): Promise<void> {
  await remove(ref(db, kullaniciYolu(uid, `gorseller/${projeId}`)));
}

/**
 * Bir defalık göç: projelerin içindeki eski kart_gorseli alanını gorseller/ yoluna
 * taşır ve proje kaydından temizler. IDB'li eski kayıtlar küçültülerek yazılır.
 */
export async function gorselleriGocEt(uid: string, projeler: { id: string; kart_gorseli?: string }[]): Promise<number> {
  let tasinan = 0;
  for (const p of projeler) {
    const eski = p.kart_gorseli;
    if (!eski) continue;
    try {
      await gorselYaz(uid, p.id, await gorseliKucult(eski));
      await update(ref(db, kullaniciYolu(uid, `projeler/${p.id}`)), { kart_gorseli: null });
      tasinan++;
    } catch (e) {
      console.warn(`[gorseller] göç başarısız (${p.id}):`, e);
    }
  }
  return tasinan;
}
