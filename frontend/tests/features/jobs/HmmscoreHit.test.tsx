import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import type { WireJob } from '@/app/api/wire'
import { hmmscoreJob, hmmscoreResult } from '@/mocks/data/jobs'
import { versions } from '@/mocks/data/versions'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const ID = '0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001'

// Columns that line up only if every space is kept, and a line too long for a phone.
const ALIGNMENT = [
  '  == domain 1  score: 439.0 bits;  conditional E-value: 7e-131',
  '  PTHR10000:SF1    1 mkvlwaallv   10',
  '                     mkvlwaallv',
  '          query    1 MKVLWAALLV   10',
  `          query   11 ${'A'.repeat(200)}`,
].join('\n')

function main() {
  return within(screen.getByRole('main'))
}

function serveJob(job: WireJob) {
  server.use(http.get('/api/v1/jobs/:id', () => HttpResponse.json(job)))
}

function succeeded(hit: (typeof hmmscoreResult)['hit']): WireJob {
  return { ...hmmscoreJob(ID, 'succeeded'), result: { hit } }
}

async function opened(job: WireJob) {
  serveJob(job)
  const rendered = renderRoute(`/jobs/${ID}`)
  await main().findByRole('status')
  return rendered
}

describe('an hmmscore job with a hit', () => {
  it('shows the PANTHER ID, name, E-value and score exactly as the API gives them', async () => {
    await opened(hmmscoreJob(ID, 'succeeded'))

    expect(main().getByText('PTHR00000:SF1')).toBeInTheDocument()
    expect(main().getByText('MOCK FAMILY')).toBeInTheDocument()
    expect(main().getByText('7e-131')).toBeInTheDocument()
    expect(main().getByText('439.0')).toBeInTheDocument()
  })

  it('links the PANTHER ID to its family page on pantherdb.org, in a new tab, saying so', async () => {
    await opened(succeeded({ ...hmmscoreResult.hit!, panther_id: 'PTHR10000:SF1 &x' }))

    const link = main().getByRole('link', { name: /PTHR10000:SF1 &x.*opens in a new tab/i })
    expect(link).toHaveAttribute(
      'href',
      'https://www.pantherdb.org/panther/family.do?clsAccession=PTHR10000%3ASF1%20%26x'
    )
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows the alignment with its spaces and line breaks kept', async () => {
    await opened(succeeded({ ...hmmscoreResult.hit!, alignment: ALIGNMENT }))

    const box = main().getByRole('region', { name: /alignment/i })
    expect(box.querySelector('pre')?.textContent).toBe(ALIGNMENT)
  })

  it('lets the keyboard reach the alignment box, named as the alignment', async () => {
    const { user } = await opened(hmmscoreJob(ID, 'succeeded'))
    const box = main().getByRole('region', { name: /alignment/i })

    for (let i = 0; i < 30 && document.activeElement !== box; i += 1) await user.tab()

    expect(box).toHaveFocus()
  })

  it("shows the job's versions with it, and is headed as HMM scoring", async () => {
    await opened(hmmscoreJob(ID, 'succeeded'))

    expect(main().getByRole('heading', { level: 2, name: /^hmm scoring$/i })).toBeVisible()
    const shown = main()
      .getByRole('heading', { name: /versions used/i })
      .closest('section')!
    expect(within(shown).getByText('API').nextSibling).toHaveTextContent(versions.api)
    expect(within(shown).getByText('Engine').nextSibling).toHaveTextContent(versions.engine)
    expect(within(shown).getByText('hmmscan').nextSibling).toHaveTextContent('3.4')
    // Traced to hmmscore's PANTHER 19 library, and only to it.
    expect(within(shown).getByText('hmmscore data').nextSibling).toHaveTextContent('PANTHER 19')
    expect(within(shown).queryByText(/csnp data|refmap data/i)).not.toBeInTheDocument()
  })
})

describe('an hmmscore job with no hit', () => {
  it('says there were no hits to PANTHER, and shows no alignment', async () => {
    await opened(succeeded(null))

    expect(main().getByText(/no hits to panther/i)).toBeInTheDocument()
    expect(main().queryByRole('region', { name: /alignment/i })).not.toBeInTheDocument()
    expect(main().queryByRole('link', { name: /pantherdb\.org/i })).not.toBeInTheDocument()
  })
})

describe('a running hmmscore job', () => {
  it('shows no hit and no alignment', async () => {
    await opened(hmmscoreJob(ID, 'running'))

    expect(main().getByRole('status')).toHaveTextContent(/running/i)
    expect(main().queryByText('PTHR00000:SF1')).not.toBeInTheDocument()
    expect(main().queryByRole('region', { name: /alignment/i })).not.toBeInTheDocument()
    expect(main().queryByText(/no hits to panther/i)).not.toBeInTheDocument()
  })
})

describe("an hmmscore job's next step", () => {
  it('links to an empty HMM scoring form', async () => {
    const { user, router } = await opened(hmmscoreJob(ID, 'running'))

    await user.click(main().getByRole('link', { name: /new hmm scoring search/i }))

    expect(router.state.location.pathname).toBe('/hmmscore')
    expect(main().getByRole('textbox', { name: /protein sequence/i })).toHaveValue('')
  })
})
