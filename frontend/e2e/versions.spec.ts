import { expect, test, type Page } from '@playwright/test'

import type { components } from '../src/app/api/schema'
import { versions as mocked } from '../src/mocks/data/versions'

type Versions = components['schemas']['Versions']

// Each label with its value, in the order the API reports them. A null version shows as
// not available.
async function expectVersionsShown(page: Page, versions: Versions) {
  const footer = page.getByRole('contentinfo')
  await expect(footer.getByRole('term')).toHaveText([
    'API',
    'Engine',
    ...versions.tools.map(tool => tool.name),
    ...versions.data.map(data => `${data.service} data`),
  ])
  await expect(footer.getByRole('definition')).toHaveText([
    versions.api,
    versions.engine,
    ...versions.tools.map(tool => tool.version ?? /not available/i),
    ...versions.data.map(data => `PANTHER ${data.panther}`),
  ])
}

test('shows the mocked versions without scrolling sideways', { tag: '@mock' }, async ({ page }) => {
  await page.goto('/')

  await expectVersionsShown(page, mocked)
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBe(0)
})

// Untagged: the versions answer is replaced in the page before any API sees the request, so
// this runs in every mode. page.route can't do it in mock mode: MSW's service worker answers
// first. Before the fix, the footer threw and React Router's developer screen replaced the page.
test('keeps the page when the versions answer has no tools or data', async ({ page }) => {
  await page.addInitScript(() => {
    const realFetch = window.fetch
    window.fetch = (input, init) => {
      const url = input instanceof Request ? input.url : String(input)
      if (new URL(url, location.href).pathname === '/api/v1/versions') {
        return Promise.resolve(
          Response.json(
            { api: '1.2.3', engine: '4.5.6' },
            { headers: { 'Cache-Control': 'no-store' } }
          )
        )
      }
      return realFetch(input, init)
    }
  })

  await page.goto('/csnp')

  const footer = page.getByRole('contentinfo')
  await expect(footer.getByRole('term')).toHaveText(['API', 'Engine'])
  await expect(footer.getByRole('definition')).toHaveText(['1.2.3', '4.5.6'])
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('main').getByLabel(/protein sequence/i)).toBeVisible()
  await expect(page.locator('body')).not.toHaveText(/hey developer|unexpected application error/i)
})

test('shows the versions the API reports', { tag: '@api' }, async ({ page }) => {
  const response = await page.request.get('/api/v1/versions')
  expect(response.ok()).toBe(true)
  const reported: Versions = await response.json()

  await page.goto('/')

  await expectVersionsShown(page, reported)
})
