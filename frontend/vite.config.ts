import { copyFileSync, rmSync } from 'node:fs'
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

// GitHub Pages answers a URL with no file, such as a reload of /jobs/<id>, with 404.html. As a
// copy of index.html, it starts the app, and the router shows the page for that URL. Every build
// gets it: other hosts ignore it, and it's the same in every mode.
function spaFallback(): Plugin {
  return {
    name: 'spa-fallback',
    apply: 'build',
    writeBundle(options) {
      if (options.dir) {
        copyFileSync(join(options.dir, 'index.html'), join(options.dir, '404.html'))
      }
    },
  }
}

// BASE_PATH, the path the site is served under: `/` by default, `/panther-scoring-services/`
// for a GitHub project page. Vite wants it with a slash at each end.
function basePath(value: string | undefined): string {
  const trimmed = (value ?? '').trim().replace(/^\/+|\/+$/g, '')
  return trimmed ? `/${trimmed}/` : '/'
}

export default defineConfig(({ mode }) => {
  // Empty prefix: also read API_PROXY_TARGET and BASE_PATH, which are never exposed to the app.
  const env = loadEnv(mode, process.cwd(), '')
  // The same .env.* value the app reads in src/app/mocking.ts.
  const mocking = env.VITE_API_MOCKING === 'on'
  // MSW answers only the relative /api/v1, so a mocked build that names a real API would call it.
  if (mocking && env.VITE_API_BASE_URL?.trim()) {
    throw new Error('VITE_API_BASE_URL must be empty when VITE_API_MOCKING is on')
  }

  // Unless VITE_API_BASE_URL is set, the app calls a relative /api, in dev and in preview.
  const proxy = {
    '/api': { target: env.API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
  }

  return {
    base: basePath(env.BASE_PATH),
    plugins: [
      react({ babel: { plugins: ['babel-plugin-react-compiler'] } }),
      tailwindcss(),
      dropMockWorker(mocking),
      spaFallback(),
    ],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: { port: 5173, proxy },
    preview: { port: 4173, strictPort: true, proxy },
  }
})
