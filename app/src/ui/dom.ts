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
export function bildirim(msg: string, tip: 'ok' | 'err' = 'ok'): void {
  const t = $('toast');
  t.textContent = (tip === 'ok' ? '✅ ' : '❌ ') + msg;
  t.className = `toast ${tip} show`;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2500);
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
