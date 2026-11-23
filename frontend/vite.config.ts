import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The UI calls the API with relative URLs (/api/...). In dev, Vite proxies them to the
// backend, so the page works from any device on the LAN with no CORS or hostname setup.
const target = process.env.VITE_PROXY_TARGET || 'http://localhost:8003'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5177,
    strictPort: true,
    host: true, // 0.0.0.0 - reachable from the LAN
    proxy: { '/api': { target, changeOrigin: true }, '/health': { target, changeOrigin: true } },
  },
  preview: { port: 5177, host: true, proxy: { '/api': { target, changeOrigin: true } } },
  build: { outDir: 'dist', sourcemap: false },
})
