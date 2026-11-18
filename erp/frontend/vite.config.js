import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// En développement, Vite sert l'interface et relaie l'API vers Django.
// En production, `npm run build` écrit dans erp/backend/frontend_dist, servi par Django.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  base: '/',
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.ERP_API_URL || 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: process.env.ERP_API_URL || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: fileURLToPath(new URL('../backend/frontend_dist', import.meta.url)),
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
});
