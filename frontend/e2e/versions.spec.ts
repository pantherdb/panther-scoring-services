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
  ])
  await expect(footer.getByRole('definition')).toHaveText([
    versions.api,
    versions.engine,
    ...versions.tools.map(tool => tool.version ?? /not available/i),
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

test('shows the versions the API reports', { tag: '@api' }, async ({ page }) => {
  const response = await page.request.get('/api/v1/versions')
  expect(response.ok()).toBe(true)
  const reported: Versions = await response.json()

  await page.goto('/')

  await expectVersionsShown(page, reported)
})
