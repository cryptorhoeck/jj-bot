import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/dashboard/',
  server: {
    // CSP - using system fonts (no external font loading needed)
    headers: {
      'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:8000 ws://127.0.0.1:8000; style-src 'self' 'unsafe-inline'; style-src-elem 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self' http://127.0.0.1:8000 ws://127.0.0.1:8000; img-src 'self' data:;"
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
})
