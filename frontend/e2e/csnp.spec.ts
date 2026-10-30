import { expect, test, type Page } from '@playwright/test'

import { csnpResult } from '../src/mocks/data/jobs'
import { versions as mockedVersions } from '../src/mocks/data/versions'

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/
const FORM_URL = /\/csnp$/

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

async function expectNoSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBe(0)
}

function fields(page: Page) {
  const main = page.getByRole('main')
  return {
    sequence: main.getByLabel(/protein sequence/i),
    substitutions: main.getByLabel(/substitutions/i),
    species: main.getByLabel(/species/i),
    submit: main.getByRole('button', { name: /score substitutions/i }),
    example: main.getByRole('button', { name: /use an example/i }),
  }
}

// From the home page, through its link, to the form filled with the example.
async function openFormWithExample(page: Page) {
  await page.goto('/')
  await page
    .getByRole('main')
    .getByRole('link', { name: /score coding snps/i })
    .click()
  await expect(page).toHaveURL(FORM_URL)
  await fields(page).example.click()
  await expect(fields(page).substitutions).toHaveValue(/L46P/)
}

// Untagged: the client checks send nothing, so this holds in every mode.
test('shows an error on each empty field, and stays on the form', async ({ page }) => {
  await page.goto('/csnp')
  const { sequence, substitutions, species, submit } = fields(page)
  await species.fill('')

  await submit.click()

  for (const field of [sequence, substitutions, species]) {
    await expect(field).toHaveAttribute('aria-invalid', 'true')
  }
  await expect(page).toHaveURL(FORM_URL)
  await expectNoBuildDetails(page)
  await expectNoSidewaysScroll(page)
})

test(
  'scores the example from the home page, and shows the mocked results with their versions',
  { tag: '@mock' },
  async ({ page }) => {
    await openFormWithExample(page)

    await fields(page).submit.click()

    await expect(page).toHaveURL(JOB_URL)
    const main = page.getByRole('main')
    await expect(main.getByRole('status')).toHaveText(/succeeded/i)
    await expect(main.getByText(csnpResult.family ?? '')).toBeVisible()
    const rows = main
      .getByRole('table', { name: /scores/i })
      .getByRole('row')
      .filter({ has: page.getByRole('cell') })
    await expect(rows).toHaveCount(csnpResult.scores.length)
    for (const [i, score] of csnpResult.scores.entries()) {
      await expect(rows.nth(i).getByRole('cell')).toHaveText([
        score.substitution,
        score.age === null ? '' : String(score.age),
        score.message,
        score.pdel ?? '',
      ])
    }
    await expect(main.getByRole('term')).toHaveText([
      'API',
      'Engine',
      ...mockedVersions.tools.map(tool => tool.name),
    ])
    await expectNoBuildDetails(page)
    await expectNoSidewaysScroll(page)
  }
)

// The @api tests below create no job: the API answers each with a 422 or its 501. So
// they're safe in site mode. The 501 test fails once cSNP scoring is ported, on purpose:
// the port removes it (add-csnp-form tasks.md, Workflow follow-up).

test(
  'says cSNP scoring is not available yet when the API answers 501, and keeps the input',
  { tag: '@api' },
  async ({ page }) => {
    await openFormWithExample(page)
    const { sequence, substitutions, species, submit } = fields(page)
    const typed = await sequence.inputValue()

    await submit.click()

    await expect(page.getByRole('main').getByRole('alert')).toHaveText(/available yet/i)
    await expect(page).toHaveURL(FORM_URL)
    await expect(sequence).toHaveValue(typed)
    await expect(substitutions).toHaveValue(/L46P\s+C130R\s+R163C\s+R176C/)
    await expect(species).toHaveValue('HUMAN')
    await expect(submit).toBeEnabled()
    await expectNoBuildDetails(page)
  }
)

test(
  "shows the API's 422 on the field it names, when a request gets past the client checks",
  { tag: '@api' },
  async ({ page }) => {
    // Rewrite the request after the client checks have passed it, so the real API's
    // validation answers: a species the client would have refused.
    await page.route('**/api/v1/jobs', async route => {
      const body = route.request().postDataJSON() as { input: Record<string, unknown> }
      await route.continue({
        postData: JSON.stringify({ ...body, input: { ...body.input, species: 'HUMAN;' } }),
      })
    })
    await openFormWithExample(page)
    const { sequence, substitutions, species, submit } = fields(page)

    await submit.click()

    await expect(species).toHaveAttribute('aria-invalid', 'true')
    await expect(sequence).not.toHaveAttribute('aria-invalid', 'true')
    await expect(substitutions).not.toHaveAttribute('aria-invalid', 'true')
    await expect(species).toHaveValue('HUMAN')
    await expect(page).toHaveURL(FORM_URL)
    await expectNoBuildDetails(page)
  }
)

test(
  'answers an invalid csnp request with a 422 whose loc names the field, as the form expects',
  { tag: '@api' },
  async ({ page }) => {
    const response = await page.request.post('/api/v1/jobs', {
      data: {
        service: 'csnp',
        input: { sequence: 'MKVLWAALLV', substitutions: ['L4P'], species: 'xyzzy;id' },
      },
    })

    expect(response.status()).toBe(422)
    const text = await response.text()
    expect(text).not.toContain('xyzzy')
    const problem = JSON.parse(text) as { errors: { loc: unknown[]; msg: unknown }[] }
    expect(problem.errors).toEqual([
      expect.objectContaining({
        loc: ['body', 'csnp', 'input', 'species'],
        msg: expect.any(String),
      }),
    ])
  }
)
