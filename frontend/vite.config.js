import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
      '/openapi.json': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})