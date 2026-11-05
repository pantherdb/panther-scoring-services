import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { csnpJob, refmapJob } from '@/mocks/data/jobs'

import { server } from '../mocks/server'
import { renderRoute } from '../utils/render'

const ID = '0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001'
const TABS = [
  /^cSNP scoring$/,
  /^ID mapping \(coming soon\)$/,
  /^HMM scoring \(coming soon\)$/,
  /^TreeGrafter \(coming soon\)$/,
]

function tabs() {
  return within(screen.getByRole('navigation', { name: /services/i })).getAllByRole('link')
}

function currentTabs() {
  return tabs().filter(tab => tab.getAttribute('aria-current') === 'page')
}

describe('the header', () => {
  it('links the title home', async () => {
    const { user } = renderRoute('/csnp')

    const title = within(screen.getByRole('heading', { level: 1 })).getByRole('link')
    expect(title).toHaveTextContent(/^PANTHER Scoring$/)
    expect(title).toHaveAttribute('href', '/')

    await user.click(title)
    expect(await screen.findByRole('link', { name: /score coding snps/i })).toBeInTheDocument()
  })

  it('lists the four services in priority order, marking the ones not available yet', () => {
    renderRoute('/')

    const shown = tabs()
    expect(shown).toHaveLength(TABS.length)
    TABS.forEach((name, i) => expect(shown[i]).toHaveAccessibleName(name))
    expect(shown.map(tab => tab.getAttribute('href'))).toEqual([
      '/csnp',
      '/refmap',
      '/hmmscore',
      '/treegrafter',
    ])
  })

  it('marks no tab as current on the home page', () => {
    renderRoute('/')

    expect(currentTabs()).toEqual([])
  })

  it.each([
    ['/csnp', /cSNP scoring/],
    ['/refmap', /ID mapping/],
    ['/hmmscore', /HMM scoring/],
  ])('marks the current page on %s', (path, name) => {
    renderRoute(path)

    expect(currentTabs()).toHaveLength(1)
    expect(currentTabs()[0]).toHaveAccessibleName(name)
  })

  it('opens a service from its tab, and marks it current', async () => {
    const { user } = renderRoute('/')

    await user.click(screen.getByRole('link', { name: /id mapping/i }))

    expect(
      await screen.findByRole('heading', { level: 2, name: /protein id mapping/i })
    ).toBeInTheDocument()
    expect(currentTabs()[0]).toHaveAccessibleName(/ID mapping/)
  })

  it.each([
    ['csnp', csnpJob(ID, 'succeeded'), /cSNP scoring/],
    ['refmap', refmapJob(ID, 'running'), /ID mapping/],
  ])("marks a %s job's service on its page", async (_service, job, name) => {
    server.use(http.get('/api/v1/jobs/:id', () => HttpResponse.json(job)))
    renderRoute(`/jobs/${ID}`)

    expect(await screen.findByRole('status')).toBeInTheDocument()
    expect(currentTabs()).toHaveLength(1)
    expect(currentTabs()[0]).toHaveAccessibleName(name)
  })

  it("marks no tab on a job's page until the job has loaded", () => {
    server.use(http.get('/api/v1/jobs/:id', () => new Promise<never>(() => {})))
    renderRoute(`/jobs/${ID}`)

    expect(screen.getByText(/loading the job/i)).toBeInTheDocument()
    expect(currentTabs()).toEqual([])
  })
})
