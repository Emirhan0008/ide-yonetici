// RTDB yardımcıları: eski shim'deki objeToArray + path çevirilerinin temiz hali.
import { off, onValue, ref } from 'firebase/database';
import { db, kullaniciYolu } from '../firebase';

/** RTDB {key: {...}} → [{id, ...}] (eski objeToArray'ın tipli hali). */
export function objeToArray<T>(v: Record<string, T> | null): (T & { id: string })[] {
  if (!v) return [];
  return Object.entries(v).map(([id, o]) => ({ ...o, id }));
}

/**
 * users/$uid/<alt> yoluna gerçek zamanlı abone olur.
 * Snapshot'lar tipli diziye çevrilip callback'e verilir.
 */
export function kullaniciDinle<T>(
  uid: string,
  alt: string,
  callback: (liste: (T & { id: string })[]) => void,
): () => void {
  const r = ref(db, kullaniciYolu(uid, alt));
  const handler = onValue(r, (snap) => callback(objeToArray<T>(snap.val())));
  return () => off(r, 'value', handler);
}
