// Firebase modular SDK (v11) — eski shim'deki compat 10.7.1'in yerine geçer.
// NOT: Firebase web yapılandırması yayına açık olmak üzere tasarlanmıştır;
// asıl güvenlik database.rules.json'daki users/$uid yalıtımıdır.
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getDatabase } from 'firebase/database';

export const FIREBASE_CONFIG = {
  apiKey: 'AIzaSyB4NKaunM5URtJJF2GQyk9TGsSGKR0YgMI',
  authDomain: 'ideyonetici-em-2026.firebaseapp.com',
  databaseURL: 'https://ideyonetici-em-2026-default-rtdb.europe-west1.firebasedatabase.app',
  projectId: 'ideyonetici-em-2026',
  storageBucket: 'ideyonetici-em-2026.firebasestorage.app',
  messagingSenderId: '773072849647',
  appId: '1:773072849647:web:d5c28e367bbb7f4770e91a',
} as const;

export const app = initializeApp(FIREBASE_CONFIG);
export const auth = getAuth(app);
export const db = getDatabase(app);

/** Kullanıcının yalıtılmış veri kökü (rules: sadece kendi uid'si). */
export function kullaniciYolu(uid: string, alt = ''): string {
  return alt ? `users/${uid}/${alt}` : `users/${uid}`;
}
