// IDE Yönetici — Duman (smoke) testleri.
// Giriş Firebase popup'ı gerektirdiğinden testler DEV test kancasıyla (window.__test)
// sahte oturum + veri enjekte eder; UI'ın uçtan uca çalıştığını doğrular.
import { expect, test, type Page } from '@playwright/test';

const PROJE = {
  ide_url: '', hesap_adi: '', hesap_email: '', sahiplik: 'Bireysel',
  notlar: '', etiketler: '', lokal_yol: '', deploy_url: '', kart_rengi: '',
};

async function sahteOturum(page: Page) {
  await page.goto('/');
  // main.ts modülü (ve DEV kancası) yüklenene kadar bekle — race condition koruması.
  await page.waitForFunction('window.__test !== undefined', null, { timeout: 10_000 });
  await page.waitForFunction('window.__test.getState().oturumHazir === true', null, { timeout: 10_000 });
  await page.evaluate((p) => {
    (window as any).__test.setState({
      kullanici: { uid: 'test', email: 'test@mail.com', ad: 'Test', resim: '' },
      oturumHazir: true, veriHazir: true,
      projeler: [
        { id: 'p1', ...p, proje_adi: 'Nashi\'nin Macerası', ide_adi: 'Cursor', ide_turu: 'Bulut', durum: 'Yarım Kaldı', sahiplik: 'Kurumsal' },
        { id: 'p2', ...p, proje_adi: 'Katibim', ide_adi: 'VS Code', ide_turu: 'Lokal', durum: 'Bitti' },
        { id: 'p3', ...p, proje_adi: 'HedefNet', ide_adi: 'Firebase Studio', ide_turu: 'Bulut', durum: 'Bitmedi ama çalışıyor' },
      ],
      ideler: [{ id: 'i1', ide_adi: 'Cursor', ide_turu: 'Bulut' }],
      hesaplar: [{ id: 'h1', hesap_adi: 'kisisel' }],
    });
  }, PROJE);
}

test('konsol hatası yok (favicon dahil)', async ({ page }) => {
  const hatalar: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') hatalar.push(m.text()); });
  await page.goto('/');
  await expect(page).toHaveTitle(/IDE Proje Takip/);
  expect(hatalar).toEqual([]);
});

test('kartlar render olur, istatistikler doğru', async ({ page }) => {
  await sahteOturum(page);
  await expect(page.locator('#kartlar .card')).toHaveCount(3);
  await expect(page.locator('#s-toplam')).toHaveText('3');
  await expect(page.locator('#s-aktif')).toHaveText('2'); // Yarım + Çalışıyor
  await expect(page.locator('#s-bitti')).toHaveText('1');
});

test('arama vurgulama + tırnaklı ad güvenle render olur', async ({ page }) => {
  await sahteOturum(page);
  await page.fill('#ara', 'nash');
  await expect(page.locator('#kartlar .card')).toHaveCount(1);
  await expect(page.locator('#kartlar mark').first()).toContainText('Nash');
});

test('istatistik kartı tıklayınca filtre uygulanır ve geri alınır', async ({ page }) => {
  await sahteOturum(page);
  await page.click('#stats .stat[data-durum="devam"]');
  await expect(page.locator('#kartlar .card')).toHaveCount(2);
  await expect(page.locator('#stats .stat[data-durum="devam"]')).toHaveClass(/secili/);
  await page.click('#stats .stat[data-durum="devam"]'); // toggle kapat
  await expect(page.locator('#kartlar .card')).toHaveCount(3);
});

test('düzenle modalı doğru veriyle açılır', async ({ page }) => {
  await sahteOturum(page);
  await page.locator('#kartlar .card [data-eylem="duzenle"]').first().click();
  await expect(page.locator('#modal-overlay')).toHaveClass(/show/);
  await expect(page.locator('#f-ide-adi')).not.toHaveValue('');
});

test('ayarlar paneli açılır, sekmeler ve ESC çalışır', async ({ page }) => {
  await sahteOturum(page);
  await page.click('#btn-ayarlar');
  await expect(page.locator('#ayar-overlay')).toHaveClass(/show/);
  await page.click('.ayar-tab[data-sec="1"]');
  await expect(page.locator('.ayar-sec[data-sec="1"]')).toHaveClass(/active/);
  await page.keyboard.press('Escape');
  await expect(page.locator('#ayar-overlay')).not.toHaveClass(/show/);
});

test('giriş yoksa giriş kapısı görünür', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#kartlar #bos-giris-btn')).toBeVisible();
});

test('açılışta yanlış boş-durum gösterilmez (iskelet → kartlar)', async ({ page }) => {
  await page.goto('/');
  await page.waitForFunction('window.__test !== undefined', null, { timeout: 10_000 });
  await page.waitForFunction('window.__test.getState().oturumHazir === true', null, { timeout: 10_000 });
  // Oturum çözüldü ama veri henüz gelmedi → "proje yok" GÖSTERİLMEZ, iskelet görünür.
  await page.evaluate(() => {
    (window as any).__test.setState({
      kullanici: { uid: 'test', email: 't@m.com', ad: '', resim: '' },
      oturumHazir: true, veriHazir: false, projeler: [],
    });
  });
  await expect(page.locator('#kartlar .iskelet').first()).toBeVisible();
  await expect(page.locator('#kartlar .empty')).toHaveCount(0);
  // Veri geldi → kartlar basılır
  await page.evaluate((p) => {
    (window as any).__test.setState({ projeler: [{ id: 'x', ...p, proje_adi: 'Geldi', ide_adi: 'VS Code', ide_turu: 'Lokal', durum: 'Bitti' }], veriHazir: true });
  }, PROJE);
  await expect(page.locator('#kartlar .card')).toHaveCount(1);
  await expect(page.locator('#kartlar .iskelet')).toHaveCount(0);
});

test('mobilde düzen dikey ve kartlar görünür', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await sahteOturum(page);
  await expect(page.locator('#kartlar .card')).toHaveCount(3);
  await expect(page.locator('.header')).toHaveCSS('flex-direction', 'column');
});

test('kart durum seçici değişikliği durumu günceller', async ({ page }) => {
  await sahteOturum(page);
  await page.locator('[data-kart="p1"] select[data-eylem="durum-sec"]').selectOption('Bitti');
  await expect.poll(async () => page.evaluate(() => {
    const p = (window as any).__test.getState().projeler.find((x: { id: string }) => x.id === 'p1');
    return p?.durum;
  })).toBe('Bitti');
});

test('çoklu seçim alt işlem çubuğunu açar', async ({ page }) => {
  await sahteOturum(page);
  await page.locator('[data-kart="p1"] input[data-eylem="kart-sec"]').check();
  await page.locator('[data-kart="p2"] input[data-eylem="kart-sec"]').check();
  await expect(page.locator('#toplu-bar')).toHaveClass(/goster/);
  await expect(page.locator('#toplu-bar')).toContainText('2 seçili');
  // Tek proje seçili kalsın, toplu işlem onu hedeflesin.
  await page.locator('[data-kart="p2"] input[data-eylem="kart-sec"]').uncheck();
  await expect(page.locator('#toplu-bar')).toContainText('1 seçili');
  await page.locator('#toplu-bar [data-toplu="bitti"]').click();
  await expect.poll(async () => page.evaluate(() => {
    const p = (window as any).__test.getState().projeler.find((x: { id: string }) => x.id === 'p1');
    return p?.durum;
  })).toBe('Bitti');
});

test('kanban görünümü sütunları basar ve sürükle-bırak durumu değiştirir', async ({ page }) => {
  await sahteOturum(page);
  await page.locator('#gorunum-kanban').click();
  await expect(page.locator('#kanban')).toHaveClass(/aktif/);
  await expect(page.locator('#kanban .kb-kolon')).toHaveCount(5);

  const birakilan = await page.evaluate(() => {
    const kart = document.querySelector<HTMLElement>('#kanban .kb-kart[data-kart="p1"]');
    const kolon = document.querySelector<HTMLElement>('#kanban .kb-kolon[data-durum="Arşiv"]');
    if (!kart || !kolon) throw new Error('Kanban kartı veya Arşiv sütunu bulunamadı');
    const dt = new DataTransfer();
    kart.dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer: dt }));
    kolon.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
    kolon.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
    return kart.dataset.kart;
  });
  expect(birakilan).toBe('p1');
  await expect.poll(async () => page.evaluate(() => {
    const p = (window as any).__test.getState().projeler.find((x: { id: string }) => x.id === 'p1');
    return p?.durum;
  })).toBe('Arşiv');
});

test('sıralama seçimi liste sırasını değiştirir', async ({ page }) => {
  await sahteOturum(page);
  await page.evaluate((p) => {
    (window as any).__test.setState({
      projeler: [
        { id: 'p1', ...p, proje_adi: 'Zeta', ide_adi: 'VS Code', ide_turu: 'Lokal', durum: 'Bitti', guncelleme_tarihi: '2026-11-02T10:00:00.000Z' },
        { id: 'p2', ...p, proje_adi: 'Alfa', ide_adi: 'Cursor', ide_turu: 'Bulut', durum: 'Yarım Kaldı', guncelleme_tarihi: '2026-11-01T10:00:00.000Z' },
      ],
    });
  }, PROJE);
  await page.locator('#f-sira').selectOption('az');
  const basliklar = await page.locator('#kartlar .card .card-title').allTextContents();
  expect(basliklar).toEqual([...basliklar].sort((a, b) => a.localeCompare(b, 'tr')));
  await expect(page.locator('#kartlar .card .card-title').first()).toHaveText('Alfa');
});
