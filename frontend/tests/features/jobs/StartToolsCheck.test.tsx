import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/

function checkButton() {
  return within(screen.getByRole('main')).getByRole('button', { name: /check the scoring tools/i })
}

// Starts a mocked job as the default handler does, after `gate` resolves, and
// records each request body.
function serveStart(gate: Promise<void> = Promise.resolve()) {
  const bodies: unknown[] = []
  server.use(
    http.post('/api/v1/jobs', async ({ request }) => {
      bodies.push(await request.json())
      await gate
      const job = createJob()
      return HttpResponse.json(job, {
        status: 202,
        headers: { Location: `/api/v1/jobs/${job.id}` },
      })
    })
  )
  return bodies
}

describe('checking the scoring tools from the home page', () => {
  it("starts a tools job and shows the job's page", async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/')

    await user.click(checkButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/jobs\/[0-9a-f-]{36}$/))
    expect(bodies).toEqual([{ service: 'tools', input: {} }])
    expect(
      await screen.findByRole('heading', { level: 2, name: /tools check/i })
    ).toBeInTheDocument()
  })

  it('is disabled while the job is being started', async () => {
    let release = () => {}
    serveStart(new Promise<void>(resolve => (release = resolve)))
    const { user, router } = renderRoute('/')
    const button = checkButton()

    await user.click(button)

    await waitFor(() => expect(button).toBeDisabled())
    expect(router.state.location.pathname).toBe('/')
    release()
    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/jobs\//))
  })

  it('says the check could not be started, with no build details, and can be tried again', async () => {
    server.use(
      http.post('/api/v1/jobs', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Internal Server Error', status: 500, detail: 'at /opt/x' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } }
        )
      )
    )
    const { user, router } = renderRoute('/')

    await user.click(checkButton())

    const alert = await within(screen.getByRole('main')).findByRole('alert')
    expect(alert).toHaveTextContent(/couldn.t be started/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(/500|internal server error/i)
    expect(router.state.location.pathname).toBe('/')
    expect(checkButton()).toBeEnabled()

    serveStart()
    await user.click(checkButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/jobs\//))
  })

  it.each([
    ['the network fails', () => HttpResponse.error()],
    [
      'the dev proxy has no API behind it',
      () => new HttpResponse(null, { status: 500, headers: { 'Content-Type': 'text/plain' } }),
    ],
  ])("says the scoring service can't be reached when %s", async (_, answer) => {
    server.use(http.post('/api/v1/jobs', answer))
    const { user, router } = renderRoute('/')

    await user.click(checkButton())

    const alert = await within(screen.getByRole('main')).findByRole('alert')
    expect(alert).toHaveTextContent(/can.t be reached/i)
    expect(alert).not.toHaveTextContent(/couldn.t be started/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(router.state.location.pathname).toBe('/')
    expect(checkButton()).toBeEnabled()
  })

  it('keeps the home page content above it', () => {
    renderRoute('/')

    expect(screen.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
    expect(checkButton()).toBeEnabled()
  })
})
