import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import type { components } from '@/app/api/schema'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

type Versions = components['schemas']['Versions']

const reported: Versions = {
  api: '1.2.3',
  engine: '4.5.6',
  tools: [
    { name: 'blastp', version: '2.17.0' },
    { name: 'hmmscan', version: '3.4' },
    { name: 'hmmsearch', version: '3.4' },
    { name: 'epa-ng', version: '0.3.8' },
  ],
}

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/

function reportVersions(body: Versions) {
  server.use(http.get('/api/v1/versions', () => HttpResponse.json(body)))
}

// The versions as the user reads them: each label with the value shown next to it.
async function shownVersions() {
  const footer = screen.getByRole('contentinfo')
  const labels = await within(footer).findAllByRole('term')
  const values = within(footer).getAllByRole('definition')
  return labels.map((label, i) => [label.textContent, values[i]?.textContent])
}

describe('versions on every page', () => {
  it('shows the API, engine and tool versions in the order reported, after loading', async () => {
    reportVersions(reported)
    renderRoute('/')

    expect(within(screen.getByRole('contentinfo')).getByText(/loading/i)).toBeInTheDocument()
    expect(await shownVersions()).toEqual([
      ['API', '1.2.3'],
      ['Engine', '4.5.6'],
      ['blastp', '2.17.0'],
      ['hmmscan', '3.4'],
      ['hmmsearch', '3.4'],
      ['epa-ng', '0.3.8'],
    ])
    expect(within(screen.getByRole('contentinfo')).queryByText(/loading/i)).not.toBeInTheDocument()
  })

  it('shows a tool with a null version as not available, and the other tools', async () => {
    reportVersions({
      ...reported,
      tools: [...reported.tools.slice(0, 3), { name: 'epa-ng', version: null }],
    })
    renderRoute('/')

    const shown = await shownVersions()
    expect(shown).toContainEqual(['epa-ng', 'not available'])
    expect(shown).toContainEqual(['blastp', '2.17.0'])
    expect(shown).toContainEqual(['hmmscan', '3.4'])
    expect(shown).toContainEqual(['hmmsearch', '3.4'])
  })

  it('says the versions are unavailable when the request fails, and the page still works', async () => {
    server.use(
      http.get('/api/v1/versions', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Internal Server Error', status: 500, detail: 'Failed.' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } }
        )
      )
    )
    renderRoute('/')

    const footer = screen.getByRole('contentinfo')
    expect(await within(footer).findByText(/unavailable/i)).toBeInTheDocument()
    expect(within(footer).queryAllByRole('term')).toHaveLength(0)
    expect(footer.textContent).not.toMatch(/\d+\.\d+/)
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
  })

  it('shows the versions on the not-found page too', async () => {
    reportVersions(reported)
    renderRoute('/does-not-exist')

    expect(await shownVersions()).toContainEqual(['blastp', '2.17.0'])
    expect(screen.getByRole('heading', { level: 2, name: /not found/i })).toBeInTheDocument()
  })

  it('shows no build details with the versions', async () => {
    reportVersions(reported)
    renderRoute('/')

    await shownVersions()
    expect(screen.getByRole('contentinfo').textContent).not.toMatch(BUILD_DETAILS)
  })
})
