import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'

import { example } from '../src/features/refmap/example'
import { EXAMPLE_MAPPINGS, refmapResult } from '../src/mocks/data/jobs'
import { versions as mockedVersions } from '../src/mocks/data/versions'
import { expectNoSidewaysScroll } from './layout'

const BUILD_DETAILS = /localhost|127\.0\.0\.1|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
const JOB_URL = /\/jobs\/[0-9a-f-]{36}$/
const FORM_URL = /\/refmap$/

const EXAMPLE_IDS = example.ids.split('\n')
const ENDPU = 'Endocarpon pusillum (ENDPU)'

async function expectNoBuildDetails(page: Page) {
  await expect(page.locator('body')).not.toHaveText(BUILD_DETAILS)
}

function fields(page: Page) {
  const main = page.getByRole('main')
  return {
    ids: main.getByRole('textbox', { name: /protein ids/i }),
    organism: main.getByRole('combobox', { name: /organism/i }),
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
  await expect(fields(page).organism).toBeEnabled()
  await fields(page).example.click()
  await expect(fields(page).organism).toHaveValue(ENDPU)
}

// Types `text` in the organism selector, once the list has loaded, and clicks the option named
// `option`. The options are in a portal, outside <main>.
async function chooseOrganism(page: Page, text: string, option: string) {
  const { organism } = fields(page)
  await expect(organism).toBeEnabled()
  await organism.click()
  await organism.fill(text)
  await page.getByRole('option', { name: option }).click()
  await expect(organism).toHaveValue(option)
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
  await expect(organism).toBeEnabled()

  await submit.click()

  await expect(ids).toHaveAttribute('aria-invalid', 'true')
  await expect(organism).toHaveAttribute('aria-invalid', 'true')
  await expect(page).toHaveURL(FORM_URL)
  await expectNoBuildDetails(page)
  await expectNoSidewaysScroll(page)
})

test(
  "chooses an organism, then maps the example from the home page, and shows the golden's mappings, summary and versions",
  { tag: '@mock' },
  async ({ page }) => {
    await page.goto('/')
    await page
      .getByRole('main')
      .getByRole('link', { name: /map protein ids/i })
      .click()
    await chooseOrganism(page, 'eco57', 'Escherichia coli O157:H7 (ECO57)')
    await fields(page).example.click()
    await expect(fields(page).organism).toHaveValue(ENDPU)
    await expect(page.getByRole('main').getByText('6 IDs will be sent.')).toBeVisible()
    const request = page.waitForRequest(
      request => request.url().endsWith('/api/v1/jobs') && request.method() === 'POST'
    )

    await fields(page).submit.click()

    const body = (await request).postDataJSON() as { input: { organism: string; ids: string[] } }
    expect(body.input).toEqual({ organism: 'ENDPU', ids: EXAMPLE_IDS })
    await expect(page).toHaveURL(JOB_URL)
    const main = page.getByRole('main')
    await expect(main.getByRole('status')).toHaveText(/succeeded/i)
    // The mocks map the example's IDs to the legacy service's answers.
    const mappings = EXAMPLE_IDS.map(id => ({ id, panther_id: EXAMPLE_MAPPINGS[id] ?? null }))
    expect(mappings).toEqual(refmapResult(EXAMPLE_IDS).mappings)
    await expect(main.getByText(`Mapped against ${ENDPU}.`)).toBeVisible()
    await expect(main.getByText(/^6 IDs: 5 have a PANTHER ID, 1 has none\.$/)).toBeVisible()
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
    await chooseOrganism(page, 'pusill', ENDPU)
    await expect(organism).toHaveValue(ENDPU)
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
