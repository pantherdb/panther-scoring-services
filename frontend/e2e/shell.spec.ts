import { expect, test, type Page } from '@playwright/test'

// Untagged: the shell makes no API calls, so this runs in every mode.

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

test('shows the title on the home page', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('main').getByRole('heading', { level: 2 })).toBeVisible()
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

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBe(0)
})
