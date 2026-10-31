import { expect, test, type Page } from '@playwright/test'

// The mock data banner: on every page in mock mode, on none against the real API.

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|MSW|npm |npx /
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/

function banner(page: Page) {
  return page.getByRole('region', { name: /mock data/i })
}

async function expectNoSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBe(0)
}

async function expectBanner(page: Page) {
  await expect(banner(page)).toBeVisible()
  await expect(banner(page)).toHaveText(/mock data/i)
  await expect(banner(page)).toHaveText(/scoring service/i)
  await expect(banner(page)).not.toHaveText(BUILD_DETAILS)
  await expectNoSidewaysScroll(page)
}

test('marks every page as mock data', { tag: '@mock' }, async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('main').getByRole('heading', { level: 2 }).first()).toBeVisible()
  await expectBanner(page)

  await page.goto('/does-not-exist')
  await expect(page.getByRole('heading', { level: 2, name: /not found/i })).toBeVisible()
  await expectBanner(page)

  // Mocked jobs live in the page, so reach the job's page through the form, without a reload.
  await page.goto('/csnp')
  const main = page.getByRole('main')
  await expect(main.getByLabel(/species/i)).toBeVisible()
  await expectBanner(page)

  await main.getByRole('button', { name: /use an example/i }).click()
  await main.getByRole('button', { name: /score substitutions/i }).click()
  await expect(page).toHaveURL(JOB_URL)
  await expect(main.getByRole('status')).toHaveText(/succeeded/i)
  await expect(main.getByRole('table', { name: /scores/i })).toBeVisible()
  await expectBanner(page)

  // Still in view at the end of the page, so any screenshot of it shows the banner. The
  // results fit both projects' screens, so shorten the window until the page scrolls.
  const { width } = page.viewportSize() ?? { width: 400 }
  await page.setViewportSize({ width, height: 400 })
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  await expect(page.getByRole('contentinfo')).toBeInViewport()
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(200)
  await expect(banner(page)).toBeInViewport()
})

test('shows no mock data banner against the real API', { tag: '@api' }, async ({ page }) => {
  for (const [path, heading] of [
    ['/', page.getByRole('main').getByRole('heading', { level: 2 }).first()],
    ['/csnp', page.getByRole('main').getByLabel(/species/i)],
    ['/refmap', page.getByRole('main').getByRole('textbox', { name: /organism/i })],
    ['/does-not-exist', page.getByRole('heading', { level: 2, name: /not found/i })],
  ] as const) {
    await page.goto(path)
    await expect(heading).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(banner(page)).toHaveCount(0)
    await expect(page.getByText(/mock data/i)).toHaveCount(0)
  }
})
