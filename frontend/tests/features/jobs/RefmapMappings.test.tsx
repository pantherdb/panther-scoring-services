import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { WireJob } from '@/app/api/wire'
import { refmapJob } from '@/mocks/data/jobs'
import { versions } from '@/mocks/data/versions'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const ID = '0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001'

type Mapping = { id: string; panther_id: string | null }

// A succeeded refmap job with these mappings, made up for the test.
function serveMappings(mappings: Mapping[]) {
  const job: WireJob = { ...refmapJob(ID, 'succeeded'), result: { mappings } }
  server.use(http.get('/api/v1/jobs/:id', () => HttpResponse.json(job)))
}

function main() {
  return within(screen.getByRole('main'))
}

async function table() {
  return main().findByRole('table', { name: /mappings/i })
}

// The table's body rows, as their cells' text. The rows by role, their cells by `cells`:
// asking for each row's cells by role takes seconds for a page of 100 rows under jsdom.
async function rows() {
  return within(await table())
    .getAllByRole('row')
    .slice(1)
    .map(row => Array.from((row as HTMLTableRowElement).cells, cell => cell.textContent))
}

function manyMappings(count: number): Mapping[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `P${i + 1}`,
    panther_id: i % 4 === 0 ? null : `PTHR00000:SF${i % 10}`,
  }))
}

const FEW: Mapping[] = [
  { id: 'P04217', panther_id: 'PTHR00000:SF4' },
  { id: 'P38398', panther_id: null },
  { id: 'P04217', panther_id: 'PTHR00000:SF4' },
]

describe('a refmap job on the job page', () => {
  it('shows its title, a summary, every mapping in order, and its versions', async () => {
    serveMappings(FEW)
    renderRoute(`/jobs/${ID}`)

    expect(await main().findByRole('heading', { name: /protein id mapping/i })).toBeVisible()
    expect(main().getByText(/^3 IDs: 2 have a PANTHER ID, 1 has none\.$/)).toBeInTheDocument()
    expect(await rows()).toEqual([
      ['1', 'P04217', 'PTHR00000:SF4'],
      ['2', 'P38398', 'No PANTHER ID'],
      ['3', 'P04217', 'PTHR00000:SF4'],
    ])
    expect(
      main()
        .getAllByRole('term')
        .map(term => term.textContent)
    ).toEqual([
      'API',
      'Engine',
      ...versions.tools.map(tool => tool.name),
      ...versions.data.map(data => `${data.service} data`),
    ])
    expect(main().queryByRole('navigation', { name: /pages/i })).toBeNull()
  })

  it('words the summary for one ID', async () => {
    serveMappings([{ id: 'P04217', panther_id: null }])
    renderRoute(`/jobs/${ID}`)

    expect(await main().findByText(/^1 ID: 0 have a PANTHER ID, 1 has none\.$/)).toBeVisible()
  })

  it('shows no table rows and no download for no mappings', async () => {
    serveMappings([])
    renderRoute(`/jobs/${ID}`)

    expect(await main().findByText(/^0 IDs:/)).toBeVisible()
    expect(await rows()).toEqual([])
    expect(main().getByRole('button', { name: /download/i })).toBeDisabled()
  })

  it('shows no mappings while the job runs', async () => {
    server.use(http.get('/api/v1/jobs/:id', () => HttpResponse.json(refmapJob(ID, 'running'))))
    renderRoute(`/jobs/${ID}`)

    expect(await main().findByRole('status')).toHaveTextContent(/running/i)
    expect(main().queryByRole('table', { name: /mappings/i })).toBeNull()
  })
})

// A page of 100 rows makes every query by role slow under jsdom, so these allow more time.
describe('a large refmap result', { timeout: 20_000 }, () => {
  it('shows 100 rows a page, and moves between pages', async () => {
    serveMappings(manyMappings(250))
    const { user } = renderRoute(`/jobs/${ID}`)

    const first = await rows()
    expect(first).toHaveLength(100)
    expect(first[0]).toEqual(['1', 'P1', 'No PANTHER ID'])
    const pages = main().getByRole('navigation', { name: /pages of mappings/i })
    expect(within(pages).getByText(/rows 1 to 100 of 250/i)).toBeVisible()

    await user.click(within(pages).getByRole('button', { name: 'Page 3' }))

    const third = await rows()
    expect(third).toHaveLength(50)
    expect(third[0]).toEqual(['201', 'P201', 'No PANTHER ID'])
    expect(within(pages).getByText(/rows 201 to 250 of 250/i)).toBeVisible()

    await user.click(within(pages).getByRole('button', { name: /previous page/i }))

    expect((await rows())[0]?.[1]).toBe('P101')
  })

  it('renders 100,000 mappings a page at a time, and reaches the last page', async () => {
    serveMappings(manyMappings(100_000))
    const { user } = renderRoute(`/jobs/${ID}`)

    expect(
      await main().findByText(/^100,000 IDs: 75,000 have a PANTHER ID, 25,000 have none\.$/)
    ).toBeVisible()
    expect(await rows()).toHaveLength(100)
    const pages = main().getByRole('navigation', { name: /pages of mappings/i })

    await user.click(within(pages).getByRole('button', { name: 'Page 1000' }))

    expect((await rows()).at(-1)).toEqual(['100,000', 'P100000', 'PTHR00000:SF9'])
    expect(within(pages).getByText(/rows 99,901 to 100,000 of 100,000/i)).toBeVisible()
  })
})

describe('downloading the mappings', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('saves every mapping, on every page, as a TSV file named after the job', async () => {
    const saved: Blob[] = []
    const names: string[] = []
    URL.createObjectURL = vi.fn((blob: Blob) => {
      saved.push(blob)
      return 'blob:mappings'
    })
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      names.push(this.download)
    })
    serveMappings(manyMappings(150))
    const { user } = renderRoute(`/jobs/${ID}`)

    await user.click(await main().findByRole('button', { name: /download the mappings/i }))

    expect(names).toEqual([`panther-id-mapping-${ID}.tsv`])
    expect(saved).toHaveLength(1)
    expect(saved[0]?.type).toBe('text/tab-separated-values')
    const lines = (await saved[0]!.text()).split('\n')
    expect(lines.slice(0, 3)).toEqual(['id\tpanther_id', 'P1\t', 'P2\tPTHR00000:SF1'])
    expect(lines).toHaveLength(152)
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mappings'))
  })
})
