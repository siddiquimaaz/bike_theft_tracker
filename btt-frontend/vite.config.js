import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    // Proxy keeps CORS from ever being an issue in dev
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
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
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          http: ['axios'],
        },
      },
    },
  },
})
