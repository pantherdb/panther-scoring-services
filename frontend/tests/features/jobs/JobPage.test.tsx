import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import type { WireJob } from '@/app/api/wire'
import {
  csnpJob,
  csnpResult,
  jobError,
  jobNotFound,
  toolsJob,
  toolsResult,
} from '@/mocks/data/jobs'
import { versions } from '@/mocks/data/versions'
import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const ID = '0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001'
const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/
const PROBLEM = { 'Content-Type': 'application/problem+json' }

// The page polls once a second, so a status change can take that long to show.
const POLL = { timeout: 3000 }

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Answers every poll of the job with `body`, and counts the polls.
function serveJob(body: WireJob | (() => Response)) {
  const calls = { count: 0 }
  server.use(
    http.get('/api/v1/jobs/:id', () => {
      calls.count += 1
      return typeof body === 'function' ? body() : HttpResponse.json(body)
    })
  )
  return calls
}

function serveProblem(status: number, problem = jobNotFound) {
  return serveJob(() => HttpResponse.json({ ...problem, status }, { status, headers: PROBLEM }))
}

function main() {
  return within(screen.getByRole('main'))
}

async function shownStatus() {
  return (await main().findByRole('status')).textContent
}

// The result table's rows as [tool, version] pairs, without the header row.
function resultRows() {
  const table = main().getByRole('table', { name: /tools/i })
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map(row =>
      within(row)
        .getAllByRole('cell')
        .map(cell => cell.textContent)
    )
}

// The job's own versions, on the page rather than in the footer.
function jobVersions() {
  const labels = main().getAllByRole('term')
  const values = main().getAllByRole('definition')
  return labels.map((label, i) => [label.textContent, values[i]?.textContent])
}

describe('the job page', () => {
  it('says the job is loading, then shows its service and status', async () => {
    const { id } = createJob()
    renderRoute(`/jobs/${id}`)

    expect(main().getByText(/loading the job/i)).toBeInTheDocument()
    expect(
      await main().findByRole('heading', { level: 2, name: /tools check/i })
    ).toBeInTheDocument()
    expect(await shownStatus()).toMatch(/queued/i)
    expect(main().queryByText(/loading the job/i)).not.toBeInTheDocument()
  })

  it('shows queued, then running, then succeeded, without a reload', async () => {
    const { id } = createJob()
    renderRoute(`/jobs/${id}`)

    expect(await shownStatus()).toMatch(/queued/i)
    await waitFor(() => expect(main().getByRole('status')).toHaveTextContent(/running/i), POLL)
    expect(main().queryByRole('table')).not.toBeInTheDocument()
    await waitFor(() => expect(main().getByRole('status')).toHaveTextContent(/succeeded/i), POLL)
    expect(main().getByRole('table', { name: /tools/i })).toBeInTheDocument()
  }, 10_000)

  it.each(['succeeded', 'failed'] as const)(
    'stops checking the job once it has %s',
    async status => {
      const calls = serveJob(toolsJob(ID, status))
      renderRoute(`/jobs/${ID}`)

      await waitFor(() =>
        expect(main().getByRole('status')).toHaveTextContent(new RegExp(status, 'i'))
      )
      await sleep(1500)

      expect(calls.count).toBe(1)
    },
    10_000
  )

  it("shows a succeeded tools job's tools in order, how long it ran, and its versions", async () => {
    serveJob(toolsJob(ID, 'succeeded'))
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(resultRows()).toEqual(toolsResult.tools.map(tool => [tool.name, tool.version]))
    expect(main().getByText(/1\.5 s/)).toBeInTheDocument()
    expect(main().getByRole('heading', { name: /versions/i })).toBeInTheDocument()
    expect(jobVersions()).toEqual([
      ['API', versions.api],
      ['Engine', versions.engine],
      ...versions.tools.map(tool => [tool.name, tool.version]),
    ])
  })

  it('shows a tool with a null version as not available, and the other tools', async () => {
    const job = toolsJob(ID, 'succeeded')
    serveJob({
      ...job,
      result: { tools: [...toolsResult.tools.slice(0, 3), { name: 'epa-ng', version: null }] },
    })
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    const rows = resultRows()
    expect(rows).toContainEqual(['epa-ng', 'not available'])
    expect(rows).toContainEqual(['blastp', '2.17.0'])
    expect(rows).toContainEqual(['hmmscan', '3.4'])
    expect(rows).toContainEqual(['hmmsearch', '3.4'])
  })

  it("says a failed job failed, with its error's detail, and shows no result", async () => {
    serveJob(toolsJob(ID, 'failed'))
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/failed/i)
    const alert = main().getByRole('alert')
    expect(alert).toHaveTextContent(/failed/i)
    expect(alert).toHaveTextContent(jobError.detail)
    expect(main().queryByRole('table')).not.toBeInTheDocument()
  })

  it('says an unknown or expired job was not found, links home, and stops checking', async () => {
    const calls = serveProblem(404)
    renderRoute('/jobs/not-a-job')

    expect(
      await main().findByRole('heading', { level: 2, name: /job not found/i })
    ).toBeInTheDocument()
    expect(main().getByText(/expired/i)).toBeInTheDocument()
    expect(main().getByRole('link', { name: /home/i })).toHaveAttribute('href', '/')
    expect(main().queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)

    await sleep(1500)
    expect(calls.count).toBe(1)
  }, 10_000)

  it('finds an unknown id in the mocked API not found too', async () => {
    renderRoute(`/jobs/${ID}`)

    expect(
      await main().findByRole('heading', { level: 2, name: /job not found/i })
    ).toBeInTheDocument()
  })

  it('says the job could not be loaded when the request fails, with no status or build details', async () => {
    serveProblem(500, { ...jobNotFound, title: 'Internal Server Error', detail: 'at /opt/app' })
    renderRoute(`/jobs/${ID}`)

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/couldn.t be loaded/i)
    expect(main().getByRole('button', { name: /try again/i })).toBeEnabled()
    expect(main().queryByRole('status')).not.toBeInTheDocument()
    expect(main().queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(/500|internal server error/i)
  })

  it.each([
    ['the network fails', () => HttpResponse.error()],
    [
      'the dev proxy has no API behind it',
      () => new HttpResponse(null, { status: 500, headers: { 'Content-Type': 'text/plain' } }),
    ],
  ])(
    "says the scoring service can't be reached when %s, and offers to try again",
    async (_, answer) => {
      serveJob(answer)
      renderRoute(`/jobs/${ID}`)

      const alert = await main().findByRole('alert')
      expect(alert).toHaveTextContent(/can.t be reached/i)
      expect(alert).not.toHaveTextContent(/couldn.t be loaded/i)
      expect(main().getByRole('button', { name: /try again/i })).toBeEnabled()
      expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    }
  )

  it('shows the job after trying again, once the API answers', async () => {
    serveProblem(500)
    const { user } = renderRoute(`/jobs/${ID}`)
    await main().findByRole('alert')

    serveJob(toolsJob(ID, 'succeeded'))
    await user.click(main().getByRole('button', { name: /try again/i }))

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(main().queryByRole('alert')).not.toBeInTheDocument()
  })
})

// The score table's body rows, each as its cells' text.
function scoreRows() {
  const table = main().getByRole('table', { name: /scores/i })
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map(row =>
      within(row)
        .getAllByRole('cell')
        .map(cell => cell.textContent)
    )
}

describe('a csnp job on the job page', () => {
  it("shows a succeeded job's family, each score as given, in order, and its versions", async () => {
    serveJob(csnpJob(ID, 'succeeded'))
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(
      main().getByRole('heading', { level: 2, name: /coding snp impact scoring/i })
    ).toBeInTheDocument()
    expect(main().getByText(csnpResult.family ?? '')).toBeInTheDocument()
    expect(scoreRows()).toEqual(
      csnpResult.scores.map(score => [
        score.substitution,
        score.age === null ? '' : String(score.age),
        score.message,
        score.pdel ?? '',
      ])
    )
    expect(jobVersions()).toEqual([
      ['API', versions.api],
      ['Engine', versions.engine],
      ...versions.tools.map(tool => [tool.name, tool.version]),
    ])
  })

  it('shows a substitution that was not scored with its message, and empty age and pDel', async () => {
    serveJob({
      ...csnpJob(ID, 'succeeded'),
      result: {
        family: 'PTHR00000',
        scores: [
          { substitution: 'G129R', age: 91, message: 'a message', pdel: '0.19' },
          {
            substitution: 'XYZ',
            age: null,
            message: 'Not scored: Invalid substitution',
            pdel: null,
          },
          { substitution: 'R5C', age: 0, message: 'another message', pdel: '0.50' },
        ],
      },
    })
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(scoreRows()).toEqual([
      ['G129R', '91', 'a message', '0.19'],
      ['XYZ', '', 'Not scored: Invalid substitution', ''],
      ['R5C', '0', 'another message', '0.50'],
    ])
  })

  it('says there is no PANTHER family when the family is null, and still shows the scores', async () => {
    serveJob({ ...csnpJob(ID, 'succeeded'), result: { ...csnpResult, family: null } })
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(main().getByText(/no panther family/i)).toBeInTheDocument()
    expect(main().queryByText(/PTHR/)).not.toBeInTheDocument()
    expect(scoreRows()).toHaveLength(csnpResult.scores.length)
  })

  it('shows the family it was placed in, not "no family", when there is one', async () => {
    serveJob(csnpJob(ID, 'succeeded'))
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/succeeded/i)
    expect(main().getByText(/panther family/i)).toHaveTextContent('PTHR00000')
    expect(main().queryByText(/no panther family/i)).not.toBeInTheDocument()
  })

  it('shows no score table while the job is running', async () => {
    serveJob(csnpJob(ID, 'running'))
    renderRoute(`/jobs/${ID}`)

    expect(await shownStatus()).toMatch(/running/i)
    expect(main().queryByRole('table')).not.toBeInTheDocument()
  })
})
