// Tanımlı IDE ve hesap listeleri (users/$uid/ideler, users/$uid/hesaplar).
import { push, ref, remove } from 'firebase/database';
import { db, kullaniciYolu } from '../firebase';
import type { TanimliHesap, TanimliIde } from '../model';
import { kullaniciDinle } from './rtdb';

export function ideleriDinle(uid: string, callback: (l: TanimliIde[]) => void): () => void {
  return kullaniciDinle<Omit<TanimliIde, 'id'>>(uid, 'ideler', callback);
}

export function hesaplariDinle(uid: string, callback: (l: TanimliHesap[]) => void): () => void {
  return kullaniciDinle<Omit<TanimliHesap, 'id'>>(uid, 'hesaplar', callback);
}

export async function ideEkle(uid: string, ide: Omit<TanimliIde, 'id'>): Promise<void> {
  await push(ref(db, kullaniciYolu(uid, 'ideler')), ide);
}

export async function ideSil(uid: string, id: string): Promise<void> {
  await remove(ref(db, kullaniciYolu(uid, `ideler/${id}`)));
}

export async function hesapEkle(uid: string, hesap: Omit<TanimliHesap, 'id'>): Promise<void> {
  await push(ref(db, kullaniciYolu(uid, 'hesaplar')), hesap);
}

export async function hesapSil(uid: string, id: string): Promise<void> {
  await remove(ref(db, kullaniciYolu(uid, `hesaplar/${id}`)));
}
