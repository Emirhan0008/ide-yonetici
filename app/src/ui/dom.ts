// DOM yardımcıları — eski Utils nesnesinin tipli, modüler karşılığı.

export function $<T extends HTMLElement = HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) throw new Error(`DOM elemanı bulunamadı: #${id}`);
  return el as T;
}

export function esc(s: unknown): string {
  if (s === null || s === undefined) return '';
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string
  ));
}

/** HTML içine gömülecek JAVASCRIPT string argümanı için tek kaçış gerekmiyor:
 *  kartlar.ts inline JS kullanmıyor (data-* + delegasyon), bu yüzden esc() yeter. */
export function highlight(metin: unknown, ara: string): string {
  const guvenli = esc(metin);
  if (!ara) return guvenli;
  const re = new RegExp(`(${ara.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return guvenli.replace(re, '<mark>$1</mark>');
}

export function getIdeIcon(adi: string): string {
  if (!adi) return '🛠';
  const a = adi.toLowerCase();
  const icons: Record<string, string> = {
    cursor: '🔵', code: '🟦', vs: '🟦', replit: '🌀',
    firebase: '🔥', github: '🐙', codespace: '🐙',
    colab: '🔶', intellij: '🏮', pycharm: '🏮',
  };
  for (const key in icons) if (a.includes(key)) return icons[key];
  return '🛠';
}

let toastTimer: ReturnType<typeof setTimeout> | null = null;

/** İsteğe bağlı eylem butonlu bildirim (toast).
 *  - `tip` boşsa eski 'ok' davranışı birebir korunur (✅ + .toast.ok).
 *  - `eylem` verilirse metnin yanına .toast-eylem butonu eklenir (textContent,
 *    innerHTML kullanılmaz — XSS koruması) ve süre 6000 ms'ye çıkar.
 *  Geriye dönük uyum: iki parametreli eski çağrılar aynı davranır. */
export function bildirim(
  mesaj: string,
  tip: '' | 'err' = '',
  eylem?: { etiket: string; onClick: () => void },
): void {
  const t = $('toast');
  const tamam = tip !== 'err';
  // textContent atamak önceki eylem butonunu da temizler (buton bir daha eklenmez).
  t.textContent = (tamam ? '✅ ' : '❌ ') + mesaj;
  t.className = `toast ${tamam ? 'ok' : 'err'} show`;
  if (eylem) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'toast-eylem';
    btn.textContent = eylem.etiket;
    btn.addEventListener('click', () => {
      if (toastTimer) clearTimeout(toastTimer);
      t.classList.remove('show');
      eylem.onClick();
    });
    t.appendChild(btn);
  }
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), eylem ? 6000 : 2500);
}

/** Filtre/datalist için benzersiz, tr-sıralı liste (eski koleksiyonTopla). */
export function benzersizListe(degerler: string[]): string[] {
  const gorulen = new Set<string>();
  const sonuc: string[] = [];
  degerler.forEach((v) => {
    const t = String(v || '').trim();
    if (!t) return;
    const k = t.toLowerCase();
    if (gorulen.has(k)) return;
    gorulen.add(k);
    sonuc.push(t);
  });
  return sonuc.sort((a, b) => a.localeCompare(b, 'tr'));
}

/** Odak tuzağı: kap içinde Tab dolaşımını kilitler. Dönen fonksiyon tuzağı kaldırır. */
export function odakTuzağı(kap: HTMLElement): () => void {
  const secum = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  const klavye = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;
    const ogeler = Array.from(kap.querySelectorAll<HTMLElement>(secum)).filter((el) => el.offsetParent !== null);
    if (ogeler.length === 0) return;
    const ilk = ogeler[0];
    const son = ogeler[ogeler.length - 1];
    const aktif = document.activeElement as HTMLElement | null;
    if (e.shiftKey && (aktif === ilk || !kap.contains(aktif))) {
      e.preventDefault();
      son.focus();
    } else if (!e.shiftKey && (aktif === son || !kap.contains(aktif))) {
      e.preventDefault();
      ilk.focus();
    }
  };
  kap.addEventListener('keydown', klavye);
  return () => kap.removeEventListener('keydown', klavye);
}
