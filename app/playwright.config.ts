import { defineConfig, devices } from '@playwright/test';

// Smoke testleri Vite dev sunucusuna karşı koşar (DEV test kancası yalnızca dev'de var).
// Çalıştır: npm run test (app/ içinde)
export default defineConfig({
  testDir: './e2e',
  timeout: 20_000,
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5199',
    trace: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5199',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
