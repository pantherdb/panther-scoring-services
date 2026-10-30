import { rmSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

// MSW's worker script lives in public/, which Vite copies into every build. A build without
// mocking never registers it, so leave it out: the production build ships nothing of MSW.
function dropMockWorker(mocking: boolean): Plugin {
  return {
    name: 'drop-mock-worker',
    apply: 'build',
    writeBundle(options) {
      if (!mocking && options.dir) {
        rmSync(join(options.dir, 'mockServiceWorker.js'), { force: true })
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  // Empty prefix: also read API_PROXY_TARGET, which is never exposed to the app.
  const env = loadEnv(mode, process.cwd(), '')
  // The same .env.* value the app reads in src/app/mocking.ts.
  const mocking = env.VITE_API_MOCKING === 'on'

  // The app always calls a relative /api, in dev and in preview.
  const proxy = {
    '/api': { target: env.API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
  }

  return {
    plugins: [
      react({ babel: { plugins: ['babel-plugin-react-compiler'] } }),
      tailwindcss(),
      dropMockWorker(mocking),
    ],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: { port: 5173, proxy },
    preview: { port: 4173, strictPort: true, proxy },
  }
})
