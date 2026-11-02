// Kanban görünümü: durum sütunları + HTML5 sürükle-bırakla durum değiştirme.
// Kullanıcı verisi daima esc() ile girer (XSS); delegasyon kalıbı kartlar.ts ile birebir aynıdır.
import type { Durum, Proje } from '../model';
import { esc, getIdeIcon } from './dom';

export interface KanbanEylemleri {
  /** Kart başka sütuna bırakıldı — durum değişikliğini kalıcılaştır. */
  durumDegis(id: string, durum: Durum): void;
}

const KANBAN_DURUMLAR: Durum[] = ['Bitmedi ama çalışıyor', 'Yarım Kaldı', 'Bitti', 'Pasif', 'Arşiv'];
const KANBAN_RENK: Record<string, string> = {
  'Bitti': '#10b981', 'Yarım Kaldı': '#f97316', 'Bitmedi ama çalışıyor': '#3b82f6',
  'Pasif': '#4a546a', 'Arşiv': '#f59e0b',
};

const dinlenenler = new WeakMap<HTMLElement, KanbanEylemleri>();

function kbKartHTML(p: Proje): string {
  const renk = p.kart_rengi || KANBAN_RENK[p.durum || ''] || '#4a546a';
  return `<div class="kb-kart" draggable="true" data-kart="${esc(p.id)}" style="--kart-renk:${esc(renk)}">
    <div class="kb-baslik">${esc(p.proje_adi)}</div>
    <div class="kb-alt"><span>${getIdeIcon(p.ide_adi)}</span><span>${esc(p.ide_adi)}</span></div>
  </div>`;
}

/** Kanban görünümünü basar; sütuna bırakmada eylemler.durumDegis çağrılır. */
export function renderKanban(kap: HTMLElement, liste: Proje[], eylemler: KanbanEylemleri): void {
  dinlenenler.set(kap, eylemler);
  kap.innerHTML = KANBAN_DURUMLAR.map((durum) => {
    const kartlar = liste.filter((p) => p.durum === durum);
    return `<div class="kb-kolon" data-durum="${esc(durum)}">
      <div class="kb-kolon-baslik" style="border-color:${KANBAN_RENK[durum] || '#4a546a'}">${esc(durum)} <span class="kb-adet">${kartlar.length}</span></div>
      <div class="kb-kolon-icek">${kartlar.map(kbKartHTML).join('')}</div>
    </div>`;
  }).join('');

  if (!kap.dataset.delegeEdildi) {
    kap.dataset.delegeEdildi = '1';
    kap.addEventListener('dragstart', (e) => {
      const kart = (e.target as HTMLElement).closest<HTMLElement>('[data-kart]');
      if (!kart) return;
      e.dataTransfer?.setData('text/plain', kart.dataset.kart ?? '');
      kart.classList.add('surukleniyor');
    });
    kap.addEventListener('dragend', () => {
      kap.querySelectorAll('.surukleniyor').forEach((el) => el.classList.remove('surukleniyor'));
      kap.querySelectorAll('.kb-kolon.hedef').forEach((el) => el.classList.remove('hedef'));
    });
    kap.addEventListener('dragover', (e) => {
      const kolon = (e.target as HTMLElement).closest<HTMLElement>('.kb-kolon');
      if (!kolon) return;
      e.preventDefault();
      kap.querySelectorAll('.kb-kolon.hedef').forEach((el) => { if (el !== kolon) el.classList.remove('hedef'); });
      kolon.classList.add('hedef');
    });
    kap.addEventListener('drop', (e) => {
      const kolon = (e.target as HTMLElement).closest<HTMLElement>('.kb-kolon');
      if (!kolon) return;
      e.preventDefault();
      kolon.classList.remove('hedef');
      const id = e.dataTransfer?.getData('text/plain') ?? '';
      if (!id || !KANBAN_DURUMLAR.includes(kolon.dataset.durum as Durum)) return;
      dinlenenler.get(kap)?.durumDegis(id, kolon.dataset.durum as Durum);
    });
  }
}
