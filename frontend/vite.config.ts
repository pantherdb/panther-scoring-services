import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Empty prefix: also read API_PROXY_TARGET, which is never exposed to the app.
  const env = loadEnv(mode, process.cwd(), '')

  // The app always calls a relative /api, in dev and in preview.
  const proxy = {
    '/api': { target: env.API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
  }

  return {
    plugins: [react({ babel: { plugins: ['babel-plugin-react-compiler'] } }), tailwindcss()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: { port: 5173, proxy },
    preview: { port: 4173, strictPort: true, proxy },
  }
})
