import { defineConfig, devices } from '@playwright/test'

// Three ways to run the suite (see docs/testing/frontend.md):
//   mock  build with MSW on, serve it locally         npm run test:e2e
//   api   build with MSW off, proxy /api to the API   npm run test:e2e:api
//   site  test an already-running site, no build      E2E_BASE_URL=<url> npm run test:e2e:site
const MODES = ['mock', 'api', 'site'] as const
type Mode = (typeof MODES)[number]

function isMode(value: string): value is Mode {
  return (MODES as readonly string[]).includes(value)
}

const mode = process.env.E2E_MODE ?? 'mock'
if (!isMode(mode)) {
  throw new Error(`E2E_MODE must be one of ${MODES.join(', ')}; got "${mode}"`)
}

const PREVIEW_URL = 'http://localhost:4173'
const baseURL = mode === 'site' ? process.env.E2E_BASE_URL : PREVIEW_URL
if (!baseURL) {
  throw new Error('Site mode needs E2E_BASE_URL, the URL of the site to test')
}

// Untagged specs run in every mode. @mock specs need mock data; @api specs
// need a live API.
const grepInvert = mode === 'mock' ? /@api/ : /@mock/

// Workers load this file too; print only once, from the main process.
if (!process.env.TEST_WORKER_INDEX) {
  console.log(`[e2e] mode: ${mode}, target: ${baseURL}`)
}

export default defineConfig({
  testDir: 'e2e',
  grepInvert,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  // Site mode tests whatever is already running at E2E_BASE_URL.
  webServer:
    mode === 'site'
      ? undefined
      : {
          command: `${mode === 'mock' ? 'npm run build:e2e' : 'npm run build'} && npm run preview`,
          url: PREVIEW_URL,
          // Never reuse a server: one left running could be a build for the other mode.
          reuseExistingServer: false,
          timeout: 120_000,
        },
})
