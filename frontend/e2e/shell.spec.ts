import { expect, test, type Page } from '@playwright/test'

import { expectNoSidewaysScroll } from './layout'

// Untagged: these specs need nothing specific from the API, so they run in every mode.

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

test('shows the title on the home page', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  // One heading per service's section.
  await expect(page.getByRole('main').getByRole('heading', { level: 2 }).first()).toBeVisible()
  await expectNoBuildDetails(page)
})

test('shows the not-found page, inside the shell, for an unknown URL', async ({ page }) => {
  await page.goto('/does-not-exist')

  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { level: 2, name: /not found/i })).toBeVisible()
  await expect(page.getByRole('main').getByRole('link')).toHaveAttribute('href', '/')
  await expectNoBuildDetails(page)
})

test('goes back home from the not-found page', async ({ page }) => {
  await page.goto('/does-not-exist')

  await page.getByRole('main').getByRole('link').click()

  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { level: 2, name: /not found/i })).toBeHidden()
})

test('does not scroll sideways', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

  await expectNoSidewaysScroll(page)
})

test('goes home from the title', async ({ page }) => {
  await page.goto('/csnp')

  await page.getByRole('heading', { level: 1 }).getByRole('link').click()

  await expect(page).toHaveURL(/\/$/)
  await expect(
    page.getByRole('main').getByRole('heading', { level: 2, name: /coding snp impact scoring/i })
  ).toBeVisible()
})

test('opens each service from its tab, and marks it current', async ({ page }) => {
  await page.goto('/')
  const tabs = page.getByRole('navigation', { name: /services/i }).getByRole('link')
  await expect(tabs).toHaveCount(4)

  for (const [name, url] of [
    [/csnp/i, /\/csnp$/],
    [/id mapping/i, /\/refmap$/],
    [/hmm scoring/i, /\/hmmscore$/],
    [/treegrafter/i, /\/treegrafter$/],
  ] as const) {
    const tab = tabs.filter({ hasText: name })
    await tab.click()
    await expect(page).toHaveURL(url)
    await expect(tab).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('main').getByRole('heading', { level: 2 }).first()).toBeVisible()
    await expectNoSidewaysScroll(page)
  }
})

test('says a service without a form is coming soon', async ({ page }) => {
  await page.goto('/hmmscore')

  const main = page.getByRole('main')
  await expect(main.getByRole('heading', { level: 2 })).toBeVisible()
  await expect(main.getByText(/coming soon/i).first()).toBeVisible()
  await expect(main.getByRole('link', { name: /back to home/i })).toHaveAttribute('href', '/')
  await expectNoBuildDetails(page)
})
