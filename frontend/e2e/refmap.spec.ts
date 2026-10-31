import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'

import { example } from '../src/features/refmap/example'
import { refmapResult } from '../src/mocks/data/jobs'
import { versions as mockedVersions } from '../src/mocks/data/versions'

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/
const FORM_URL = /\/refmap$/

const EXAMPLE_IDS = example.ids.split('\n')

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
    ids: main.getByRole('textbox', { name: /protein ids/i }),
    organism: main.getByRole('textbox', { name: /organism/i }),
    file: main.getByLabel(/text file of protein ids/i),
    submit: main.getByRole('button', { name: /map ids/i }),
    example: main.getByRole('button', { name: /use an example/i }),
  }
}

// From the home page, through its link, to the form filled with the example.
async function openFormWithExample(page: Page) {
  await page.goto('/')
  await page
    .getByRole('main')
    .getByRole('link', { name: /map protein ids/i })
    .click()
  await expect(page).toHaveURL(FORM_URL)
  await fields(page).example.click()
  await expect(fields(page).organism).toHaveValue('HUMAN')
}

function bodyRows(page: Page) {
  return page
    .getByRole('main')
    .getByRole('table', { name: /mappings/i })
    .getByRole('row')
    .filter({ has: page.getByRole('cell') })
}

// Untagged: the client checks send nothing, so this holds in every mode.
test('shows an error on each empty box, and stays on the form', async ({ page }) => {
  await page.goto('/refmap')
  const { ids, organism, submit } = fields(page)

  await submit.click()

  await expect(ids).toHaveAttribute('aria-invalid', 'true')
  await expect(organism).toHaveAttribute('aria-invalid', 'true')
  await expect(page).toHaveURL(FORM_URL)
  await expectNoBuildDetails(page)
  await expectNoSidewaysScroll(page)
})

test(
  'maps the example from the home page, and shows the mocked mappings, summary and versions',
  { tag: '@mock' },
  async ({ page }) => {
    await openFormWithExample(page)
    await expect(page.getByRole('main').getByText('6 IDs will be sent.')).toBeVisible()

    await fields(page).submit.click()

    await expect(page).toHaveURL(JOB_URL)
    const main = page.getByRole('main')
    await expect(main.getByRole('status')).toHaveText(/succeeded/i)
    const { mappings } = refmapResult(EXAMPLE_IDS)
    const mapped = mappings.filter(mapping => mapping.panther_id !== null).length
    await expect(main.getByText(new RegExp(`^6 IDs: ${mapped} have`))).toBeVisible()
    await expect(bodyRows(page)).toHaveCount(mappings.length)
    for (const [i, mapping] of mappings.entries()) {
      await expect(bodyRows(page).nth(i).getByRole('cell')).toHaveText([
        String(i + 1),
        mapping.id,
        mapping.panther_id ?? 'No PANTHER ID',
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

    const download = page.waitForEvent('download')
    await main.getByRole('button', { name: /download the mappings/i }).click()
    const saved = await download
    expect(saved.suggestedFilename()).toMatch(/^panther-id-mapping-[0-9a-f-]{36}\.tsv$/)
    expect(readFileSync(await saved.path(), 'utf8')).toBe(
      [
        'id\tpanther_id',
        ...mappings.map(mapping => `${mapping.id}\t${mapping.panther_id ?? ''}`),
        '',
      ].join('\n')
    )
  }
)

test(
  'loads 100,000 IDs from a file, maps them, and pages through them',
  { tag: '@mock' },
  async ({ page }) => {
    test.setTimeout(90_000)
    const ids = Array.from({ length: 100_000 }, (_, i) => `P${String(i + 1).padStart(6, '0')}`)
    await page.goto('/refmap')
    const { file, organism, submit } = fields(page)

    await file.setInputFiles({
      name: 'ids.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(`${ids.map(id => `${id}\t1.0`).join('\n')}\n`),
    })

    const main = page.getByRole('main')
    await expect(main.getByText(/^100,000 IDs will be sent\./)).toBeVisible()
    await expect(main.getByText(/first column was read on 100,000 lines/)).toBeVisible()
    await organism.fill('HUMAN')
    await submit.click()

    await expect(page).toHaveURL(JOB_URL)
    await expect(main.getByRole('status')).toHaveText(/succeeded/i)
    await expect(main.getByText(/^100,000 IDs:/)).toBeVisible()
    await expect(bodyRows(page)).toHaveCount(100)
    await main.getByRole('button', { name: 'Page 1000' }).click()
    await expect(bodyRows(page).last().getByRole('cell').nth(1)).toHaveText('P100000')
    await expect(main.getByText(/rows 99,901 to 100,000 of 100,000/i)).toBeVisible()
    await expectNoSidewaysScroll(page)
  }
)

// The @api tests create no job: a valid request gets the API's 501 until refmap is ported, and
// an invalid one a 422.

test(
  "says ID mapping isn't available yet on the API's 501, keeping the input",
  { tag: '@api' },
  async ({ page }) => {
    await openFormWithExample(page)
    const { ids, organism, submit } = fields(page)

    await submit.click()

    const alert = page.getByRole('main').getByRole('alert')
    await expect(alert).toHaveText(/isn.t available yet/i)
    await expect(page).toHaveURL(FORM_URL)
    await expect(ids).toHaveValue(example.ids)
    await expect(organism).toHaveValue('HUMAN')
    await expect(alert).not.toHaveText(/501|not implemented/i)
    await expectNoBuildDetails(page)
    await expectNoSidewaysScroll(page)
  }
)

test(
  "shows the API's 422 on the ID it names, when a request gets past the client checks",
  { tag: '@api' },
  async ({ page }) => {
    // Rewrite the request after the client checks have passed it, so the real API's
    // validation answers: an ID with a space, which the form would have split.
    await page.route('**/api/v1/jobs', async route => {
      const body = route.request().postDataJSON() as { input: { ids: string[] } }
      const ids = body.input.ids.map((id, i) => (i === 1 ? `${id} x` : id))
      await route.continue({ postData: JSON.stringify({ ...body, input: { ...body.input, ids } }) })
    })
    await openFormWithExample(page)
    const { ids, organism, submit } = fields(page)

    await submit.click()

    await expect(ids).toHaveAttribute('aria-invalid', 'true')
    // Named from the form's own copy of what it sent: the API never echoes an ID.
    await expect(ids).toHaveAccessibleDescription(/ID 2 \(P01023, line 2\)/)
    await expect(organism).not.toHaveAttribute('aria-invalid', 'true')
    await expect(page).toHaveURL(FORM_URL)
    await expectNoBuildDetails(page)
  }
)

test(
  'answers an invalid refmap request with a 422 whose loc names the field, as the form expects',
  { tag: '@api' },
  async ({ page }) => {
    const response = await page.request.post('/api/v1/jobs', {
      data: { service: 'refmap', input: { organism: 'xyzzy|', ids: ['P04217', 'P0 1023'] } },
    })

    expect(response.status()).toBe(422)
    const text = await response.text()
    expect(text).not.toContain('xyzzy')
    expect(text).not.toContain('P0 1023')
    const problem = JSON.parse(text) as { errors: { loc: unknown[] }[] }
    expect(problem.errors.map(error => error.loc)).toEqual(
      expect.arrayContaining([
        ['body', 'refmap', 'input', 'organism'],
        ['body', 'refmap', 'input', 'ids', 1],
      ])
    )
  }
)
