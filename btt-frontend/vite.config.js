import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// BTT runs on 3001/8001 because ports 3000 and 8000 belong to MuseAI on this
// machine. Override when the Django dev server moves, e.g.
// `VITE_API_PROXY_TARGET=http://localhost:8002 npm run dev`.
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8001';
const DEV_PORT = Number(process.env.VITE_DEV_PORT ?? 3001);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: DEV_PORT,
    strictPort: true,
    // Proxy keeps CORS from ever being an issue in dev
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split the rarely-changing vendor code out of the app chunk so a
        // deploy only invalidates the app bundle, not React + Router + Axios.
        // Rolldown (Vite 8) only accepts the function form here.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (/[\\/]node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/.test(id)) {
            return 'react-vendor';
          }
          if (/[\\/]node_modules[\\/]axios[\\/]/.test(id)) return 'axios-vendor';
          return undefined;
        },
      },
    },
  },
})
