// Light/dark tema — localStorage: app_tema (eski davranışla aynı anahtar).
const ANAHTAR = 'app_tema';

export function temaUygula(tema: 'dark' | 'light'): void {
  document.documentElement.setAttribute('data-theme', tema);
}

export function temaInit(): void {
  temaUygula((localStorage.getItem(ANAHTAR) as 'dark' | 'light') || 'dark');
}

export function temaDegistir(): void {
  const suAn = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  const yeni = suAn === 'light' ? 'dark' : 'light';
  localStorage.setItem(ANAHTAR, yeni);
  temaUygula(yeni);
}
