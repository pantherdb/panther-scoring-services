import { expect, test, type Page } from '@playwright/test'

import { APOE_SEQUENCE } from '../src/components/apoe'
import { hmmscoreResult } from '../src/mocks/data/jobs'
import { expectNoSidewaysScroll } from './layout'

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
const STATUS_CODES = /\b50[0-3]\b|not implemented|service unavailable/i
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/
const FORM_URL = /\/hmmscore$/

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

function fields(page: Page) {
  const main = page.getByRole('main')
  return {
    sequence: main.getByRole('textbox', { name: /protein sequence/i }),
    submit: main.getByRole('button', { name: /score sequence/i }),
    example: main.getByRole('button', { name: /use an example/i }),
    alert: main.getByRole('alert'),
  }
}

// From the home page, through its card's link, to the form filled with the example.
async function openFormWithExample(page: Page) {
  await page.goto('/')
  await page
    .getByRole('main')
    .getByRole('link', { name: /score a protein sequence/i })
    .click()
  await expect(page).toHaveURL(FORM_URL)
  await fields(page).example.click()
  await expect(fields(page).sequence).toHaveValue(APOE_SEQUENCE)
}

// Untagged: the notice and the client checks send nothing, so this holds in every mode.
test("says HMM scoring isn't available yet, and checks an empty form", async ({ page }) => {
  await page.goto('/hmmscore')
  const main = page.getByRole('main')
  const { sequence, submit } = fields(page)
  await expect(main.getByText(/isn.t available on this site yet/i)).toBeVisible()

  await submit.click()

  await expect(sequence).toHaveAttribute('aria-invalid', 'true')
  await expect(sequence).toHaveAccessibleDescription(/no residues/i)
  await expect(page).toHaveURL(FORM_URL)
  await expectNoBuildDetails(page)
  await expectNoSidewaysScroll(page)
})

test(
  'scores the example from the home page, and shows the mocked hit and alignment',
  { tag: '@mock' },
  async ({ page }) => {
    const hit = hmmscoreResult.hit!
    await openFormWithExample(page)
    const request = page.waitForRequest(
      request => request.url().endsWith('/api/v1/jobs') && request.method() === 'POST'
    )

    await fields(page).submit.click()

    const body = (await request).postDataJSON() as unknown
    expect(body).toEqual({ service: 'hmmscore', input: { sequence: APOE_SEQUENCE } })
    await expect(page).toHaveURL(JOB_URL)
    const main = page.getByRole('main')
    await expect(main.getByRole('status')).toHaveText(/succeeded/i)
    const link = main.getByRole('link', { name: /opens in a new tab/i })
    await expect(link).toHaveText(hit.panther_id)
    await expect(link).toHaveAttribute('target', '_blank')
    await expect(main.getByText(hit.name, { exact: true })).toBeVisible()
    await expect(main.getByText(hit.evalue, { exact: true })).toBeVisible()
    await expect(main.getByText(hit.score, { exact: true })).toBeVisible()
    const box = main.getByRole('region', { name: /alignment/i })
    await expect(box).toBeVisible()
    expect(await box.locator('pre').textContent()).toBe(hit.alignment)
    await expectNoBuildDetails(page)
  }
)

test(
  'scrolls the alignment within its box, by keyboard too, and never the page',
  { tag: '@mock' },
  async ({ page }) => {
    await openFormWithExample(page)
    await fields(page).submit.click()
    const box = page.getByRole('main').getByRole('region', { name: /alignment/i })
    await expect(box).toBeVisible()

    // The mock's lines are 200 characters, wider than either project's window.
    const overflow = await box.evaluate(element => element.scrollWidth - element.clientWidth)
    expect(overflow).toBeGreaterThan(0)
    await expectNoSidewaysScroll(page)

    await box.focus()
    await expect(box).toBeFocused()
    await page.keyboard.press('ArrowRight')
    await page.keyboard.press('ArrowRight')
    await expect.poll(() => box.evaluate(element => element.scrollLeft)).toBeGreaterThan(0)
    await expectNoSidewaysScroll(page)
  }
)

// The @api tests below create no job: the API answers 501 until hmmscore is wired in, or 422.

test(
  "shows the API's 501 as not available yet, and keeps the sequence",
  { tag: '@api' },
  async ({ page }) => {
    await openFormWithExample(page)
    const { sequence, submit, alert } = fields(page)

    await submit.click()

    await expect(alert).toHaveText(/hmm scoring isn.t available yet/i)
    await expect(alert).not.toHaveText(STATUS_CODES)
    await expect(sequence).toHaveValue(APOE_SEQUENCE)
    await expect(submit).toBeEnabled()
    await expect(page).toHaveURL(FORM_URL)
    await expectNoBuildDetails(page)
  }
)

test(
  "shows the API's 422 on the sequence, when a request gets past the client checks",
  { tag: '@api' },
  async ({ page }) => {
    // Rewrite the request after the client checks have passed it, so the real API's validation
    // answers: a dash, which the form would have refused.
    await page.route('**/api/v1/jobs', async route => {
      const body = route.request().postDataJSON() as { input: { sequence: string } }
      const input = { sequence: `${body.input.sequence}-` }
      await route.continue({ postData: JSON.stringify({ ...body, input }) })
    })
    await openFormWithExample(page)
    const { sequence, submit } = fields(page)

    await submit.click()

    await expect(sequence).toHaveAttribute('aria-invalid', 'true')
    await expect(sequence).toHaveAccessibleDescription(/letters A to Z/)
    await expect(page).toHaveURL(FORM_URL)
    await expectNoBuildDetails(page)
  }
)
