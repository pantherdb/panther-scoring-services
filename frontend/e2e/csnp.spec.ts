import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { expect, test, type Page } from '@playwright/test'

import { csnpResult } from '../src/mocks/data/jobs'
import { species as mockedSpecies } from '../src/mocks/data/species'
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
    // The selector. By role: its open list of options is labelled "Species" too.
    species: main.getByRole('combobox', { name: /species/i }),
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

const HUMAN = 'Homo sapiens (HUMAN)'

// Clears the selector, types `text` in it, and clicks the option named `option`. The options
// are in a portal, outside <main>.
async function chooseSpecies(page: Page, text: string, option: string) {
  const { species } = fields(page)
  await expect(species).toHaveValue(HUMAN)
  await species.click()
  await species.fill(text)
  await page.getByRole('option', { name: option }).click()
  await expect(species).toHaveValue(option)
}

// Untagged: the client checks send nothing, so this holds in every mode.
test('shows an error on each empty box, and stays on the form', async ({ page }) => {
  await page.goto('/csnp')
  const { sequence, substitutions, species, submit } = fields(page)
  await expect(species).toHaveValue(HUMAN)

  await submit.click()

  for (const field of [sequence, substitutions]) {
    await expect(field).toHaveAttribute('aria-invalid', 'true')
  }
  // The selector can't be emptied: it still holds HUMAN.
  await expect(species).not.toHaveAttribute('aria-invalid', 'true')
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
      ...mockedVersions.data.map(data => `${data.service} data`),
    ])
    await expectNoBuildDetails(page)
    await expectNoSidewaysScroll(page)
  }
)

test(
  'chooses a species by typing part of its name, and sends its code',
  { tag: '@mock' },
  async ({ page }) => {
    await openFormWithExample(page)
    const { species, submit } = fields(page)
    // On a phone the field is below the fold: opening it must not scroll the page away from it.
    await species.click()
    await expect(page.getByRole('option')).toHaveCount(mockedSpecies.length)

    await chooseSpecies(page, 'muscul', 'Mus musculus (MOUSE)')
    const request = page.waitForRequest(
      request => request.url().endsWith('/api/v1/jobs') && request.method() === 'POST'
    )
    await submit.click()

    const body = (await request).postDataJSON() as { input: { species: string } }
    expect(body.input.species).toBe('MOUSE')
    await expect(page).toHaveURL(JOB_URL)
    await expectNoBuildDetails(page)
    await expectNoSidewaysScroll(page)
  }
)

// The release sample's first protein, P26439, and three of its substitutions with the scores
// the legacy service gave them (the engine's goldens, spec §7.3). The data sample covers its
// family, as it does the form's APOE example's (docs/testing/frontend.md).
const GOLDEN = fileURLToPath(new URL('../../engine/tests/golden/csnp/release/', import.meta.url))
const SAMPLE_PROTEIN = readFileSync(`${GOLDEN}sample.fasta`, 'utf8').split(/\n\s*\n/)[0] ?? ''
const SAMPLE_SCORES = [
  ['A10E', '220', 'possibly damaging', '0.50'],
  ['G15D', '4200', 'probably damaging', '0.95'],
  ['S213G', '91', 'probably benign', '0.19'],
]

// Creates a real job: in api mode the API needs the cSNP data sample, and in site mode the
// site does too.
test(
  'scores a protein the data sample covers, and shows its scores with the data version',
  { tag: '@api' },
  async ({ page }) => {
    // A search takes seconds, and the API's first job also starts a worker.
    test.setTimeout(90_000)
    await page.goto('/csnp')
    const { sequence, substitutions, species, submit } = fields(page)
    await sequence.fill(SAMPLE_PROTEIN)
    await substitutions.fill(SAMPLE_SCORES.map(([token]) => token).join(' '))
    await expect(species).toHaveValue(HUMAN)

    await submit.click()

    await expect(page).toHaveURL(JOB_URL)
    const main = page.getByRole('main')
    await expect(main.getByRole('status')).toHaveText(/succeeded/i, { timeout: 60_000 })
    await expect(main.getByText('PTHR10366')).toBeVisible()
    const rows = main
      .getByRole('table', { name: /scores/i })
      .getByRole('row')
      .filter({ has: page.getByRole('cell') })
    await expect(rows).toHaveCount(SAMPLE_SCORES.length)
    for (const [i, cells] of SAMPLE_SCORES.entries()) {
      await expect(rows.nth(i).getByRole('cell')).toHaveText(cells)
    }
    await expect(main.getByRole('definition').last()).toHaveText(/^PANTHER \S+$/)
    await expectNoBuildDetails(page)
    await expectNoSidewaysScroll(page)
  }
)

test("offers the API's whole species list", { tag: '@api' }, async ({ page }) => {
  const response = await page.request.get('/api/v1/csnp/species')
  expect(response.status()).toBe(200)
  const listed = (await response.json()) as { code: string; name: string }[]
  expect(listed.length).toBeGreaterThan(mockedSpecies.length)
  await page.goto('/csnp')
  const { species } = fields(page)
  await expect(species).toHaveValue(HUMAN)

  await species.click()

  const options = page.getByRole('option')
  await expect(options).toHaveCount(listed.length)
  for (const { code, name } of listed) {
    await expect(page.getByRole('option', { name: `${name} (${code})` })).toHaveCount(1)
  }
})

// Creates a real job, which runs after the test: the API needs the cSNP data sample.
test(
  'starts a job with a species chosen from the list other than HUMAN',
  { tag: '@api' },
  async ({ page }) => {
    await page.goto('/csnp')
    const { sequence, substitutions, submit } = fields(page)
    await sequence.fill(SAMPLE_PROTEIN)
    await substitutions.fill('A10E')
    await chooseSpecies(page, 'musculus', 'Mus musculus (MOUSE)')
    const request = page.waitForRequest(
      request => request.url().endsWith('/api/v1/jobs') && request.method() === 'POST'
    )

    await submit.click()

    const body = (await request).postDataJSON() as { input: { species: string } }
    expect(body.input.species).toBe('MOUSE')
    await expect(page).toHaveURL(JOB_URL)
    await expect(page.getByRole('main').getByRole('status')).toBeVisible()
    await expectNoBuildDetails(page)
  }
)

// The @api tests below create no job: the API answers each with a 422.

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
    await expect(species).toHaveValue(HUMAN)
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
