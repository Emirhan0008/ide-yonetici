// Hızlı renk paleti + rastgele renk (eski RENK_PALETI).
export const RENK_PALETI = [
  '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
  '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9',
  '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  '#ec4899', '#f43f5e', '#64748b', '#94a3b8', '#ffffff',
];

export function rastgeleRenk(): string {
  return RENK_PALETI[Math.floor(Math.random() * (RENK_PALETI.length - 2))]; // son 2 (gri/beyaz) hariç
}
