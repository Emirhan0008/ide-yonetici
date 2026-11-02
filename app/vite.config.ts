import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

// Dev sunucusu sabit portta: Playwright smoke testleri bu portu kullanır.
export default defineConfig({
  server: { port: 5199, strictPort: true },
  preview: { port: 5199, strictPort: true },
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'IDE Proje Takip',
        short_name: 'IDE Yönetici',
        description: "Projelerini, IDE'lerini ve hesaplarını tek yerden yönet.",
        start_url: '/',
        display: 'standalone',
        background_color: '#090b14',
        theme_color: '#0ea5e9',
        lang: 'tr',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        navigateFallback: '/index.html',
      },
    }),
  ],
});
