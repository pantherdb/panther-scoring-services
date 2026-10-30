import { expect, test, type Page } from '@playwright/test'

import type { components } from '../src/app/api/schema'
import { toolsResult } from '../src/mocks/data/jobs'
import { versions as mockedVersions } from '../src/mocks/data/versions'

type ToolVersion = components['schemas']['ToolVersion']
type Versions = components['schemas']['Versions']

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

async function startToolsCheck(page: Page) {
  await page.goto('/')
  await page
    .getByRole('main')
    .getByRole('button', { name: /check the scoring tools/i })
    .click()
  await expect(page).toHaveURL(JOB_URL)
}

// The result table's body rows: each tool's name, then its version or "not available".
async function expectToolsShown(page: Page, tools: ToolVersion[]) {
  const table = page.getByRole('main').getByRole('table', { name: /tools/i })
  const rows = table.getByRole('row').filter({ has: page.getByRole('cell') })
  await expect(rows).toHaveText(
    tools.map(tool => new RegExp(`${tool.name}\\s*${tool.version ?? 'not available'}`, 'i'))
  )
}

// The job's own versions, on the page rather than in the footer.
async function expectJobVersionsShown(page: Page, versions: Versions) {
  const main = page.getByRole('main')
  await expect(main.getByRole('term')).toHaveText([
    'API',
    'Engine',
    ...versions.tools.map(tool => tool.name),
  ])
  await expect(main.getByRole('definition')).toHaveText([
    versions.api,
    versions.engine,
    ...versions.tools.map(tool => tool.version ?? /not available/i),
  ])
}

// Untagged: every mode's API answers a malformed id with 404.
test('says a job that does not exist was not found, and links home', async ({ page }) => {
  await page.goto('/jobs/not-a-job')

  const main = page.getByRole('main')
  await expect(main.getByRole('heading', { level: 2, name: /job not found/i })).toBeVisible()
  await expect(main.getByRole('link', { name: /home/i })).toHaveAttribute('href', '/')
  await expectNoBuildDetails(page)
})

test(
  'checks the scoring tools from the home page, showing each status, then the result',
  { tag: '@mock' },
  async ({ page }) => {
    await startToolsCheck(page)

    const status = page.getByRole('main').getByRole('status')
    await expect(status).toHaveText(/queued/i)
    await expect(status).toHaveText(/running/i)
    await expect(status).toHaveText(/succeeded/i)
    await expectToolsShown(page, toolsResult.tools)
    await expectJobVersionsShown(page, mockedVersions)
    await expectNoBuildDetails(page)

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    )
    expect(overflow).toBe(0)
  }
)

// Starting a tools job is harmless on a shared deployment, so this is safe in site mode.
test(
  'checks the scoring tools against the API, and keeps the result at its URL',
  { tag: '@api' },
  async ({ page }) => {
    const response = await page.request.get('/api/v1/versions')
    expect(response.ok()).toBe(true)
    const reported: Versions = await response.json()

    await startToolsCheck(page)

    const status = page.getByRole('main').getByRole('status')
    // The API's first job also starts a worker process, which takes a second or two.
    await expect(status).toHaveText(/succeeded/i, { timeout: 15_000 })
    await expectToolsShown(page, reported.tools)
    await expectJobVersionsShown(page, reported)

    await page.reload()

    await expect(status).toHaveText(/succeeded/i)
    await expectToolsShown(page, reported.tools)
  }
)
