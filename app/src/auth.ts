// Kimlik doğrulama — Firebase Auth (Google). Eski shim'deki GIS-buton/dropdown
// karmaşası yerine modüler SDK'nın kendi popup akışı kullanılır; popup engellenirse
// redirect'e düşülür (eski davranışla aynı garanti).
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from 'firebase/auth';
import { getRedirectResult } from 'firebase/auth';
import type { User } from 'firebase/auth';
import { auth } from './firebase';
import type { KullaniciProfili } from './model';

const saglayici = new GoogleAuthProvider();

function profile(u: User): KullaniciProfili {
  return {
    uid: u.uid,
    email: u.email ?? '',
    ad: u.displayName ?? '',
    resim: u.photoURL ?? '',
  };
}

export async function girisYap(): Promise<void> {
  try {
    await signInWithPopup(auth, saglayici);
  } catch (e) {
    const kod = (e as { code?: string }).code ?? '';
    if (kod === 'auth/popup-blocked' || kod === 'auth/unsupported-popup-redirect-mode') {
      await signInWithRedirect(auth, saglayici);
      return;
    }
    if (kod === 'auth/popup-closed-by-user' || kod === 'auth/cancelled-popup-request') return;
    throw e;
  }
}

export async function cikisYap(): Promise<void> {
  await signOut(auth);
}

/** Auth durumu değişimlerine abone olur; oturum açılışındaki redirect sonucunu da emer. */
export function authAboneOl(dinleyici: (p: KullaniciProfili | null) => void): () => void {
  const iptal = onAuthStateChanged(auth, (u) => dinleyici(u ? profile(u) : null));
  getRedirectResult(auth).catch((e: { code?: string; message?: string }) => {
    if (e.code !== 'auth/no-auth-event' && e.code !== 'auth/null-user') {
      console.error('[auth] redirect sonucu:', e.code, e.message);
    }
  });
  return iptal;
}
