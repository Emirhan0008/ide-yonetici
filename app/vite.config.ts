import { defineConfig } from 'vite';

// Dev sunucusu sabit portta: Playwright smoke testleri bu portu kullanır.
export default defineConfig({
  server: { port: 5199, strictPort: true },
  preview: { port: 5199, strictPort: true },
});
