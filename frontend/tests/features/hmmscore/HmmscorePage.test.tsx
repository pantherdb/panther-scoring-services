import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/
const PROBLEM = { 'Content-Type': 'application/problem+json' }
const JOB_PATH = /^\/jobs\/[0-9a-f-]{36}$/
const STATUS_CODES = /\b50[0-3]\b|not implemented|service unavailable|internal server error/i

const VALID = '>sp|P02649|APOE_HUMAN\nmkvl waal\n'

function main() {
  return within(screen.getByRole('main'))
}

function sequenceBox() {
  return main().getByRole('textbox', { name: /protein sequence/i })
}

function submitButton() {
  return main().getByRole('button', { name: /score sequence/i })
}

function letters(count: number) {
  return 'MKVLWAALLV'.repeat(Math.ceil(count / 10)).slice(0, count)
}

// Answers POST /jobs with `answer`, or, by default, as the mocked API does (a queued hmmscore
// job), after `gate` resolves. Records each request body.
function serveStart(
  answer: (() => Response) | undefined = undefined,
  gate: Promise<void> = Promise.resolve()
) {
  const bodies: unknown[] = []
  server.use(
    http.post('/api/v1/jobs', async ({ request }) => {
      bodies.push(await request.json())
      await gate
      if (answer) return answer()
      const job = createJob('hmmscore')
      return HttpResponse.json(job, {
        status: 202,
        headers: { Location: `/api/v1/jobs/${job.id}` },
      })
    })
  )
  return bodies
}

function problem(status: number, title: string) {
  return { type: 'about:blank', title, status, detail: 'at /opt/app on :8000' }
}

function serveProblem(status: number, body: object, headers: Record<string, string> = {}) {
  return serveStart(() => HttpResponse.json(body, { status, headers: { ...PROBLEM, ...headers } }))
}

function serveValidationProblem(...errors: { loc: (string | number)[]; msg: string }[]) {
  return serveProblem(422, {
    ...problem(422, 'Unprocessable Content'),
    detail: 'Request validation failed',
    errors: errors.map(error => ({ ...error, type: 'value_error' })),
  })
}

// Sets the box's text at once: typing or pasting a million characters is slow.
function enter(text: string) {
  fireEvent.change(sequenceBox(), { target: { value: text } })
}

// The form stays at /hmmscore, keeps the sequence and can be submitted again, which now opens
// the job.
async function keptAndUsable({ user, router }: ReturnType<typeof renderRoute>, text: string) {
  expect(router.state.location.pathname).toBe('/hmmscore')
  expect(sequenceBox()).toHaveValue(text)
  expect(submitButton()).toBeEnabled()
  serveStart()
  await user.click(submitButton())
  await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
}

describe('the HMM scoring form', () => {
  it('opens from the home page, with an empty box', async () => {
    const { user, router } = renderRoute('/')

    await user.click(main().getByRole('link', { name: /score a protein sequence/i }))

    expect(router.state.location.pathname).toBe('/hmmscore')
    expect(main().getByRole('heading', { level: 2, name: /hmm scoring/i })).toBeVisible()
    expect(sequenceBox()).toHaveValue('')
    expect(submitButton()).toBeEnabled()
  })

  it('opens from its tab, which is marked current', async () => {
    const { user, router } = renderRoute('/')
    const tabs = within(screen.getByRole('navigation', { name: /services/i }))

    await user.click(tabs.getByRole('link', { name: /hmm scoring/i }))

    expect(router.state.location.pathname).toBe('/hmmscore')
    expect(sequenceBox()).toHaveValue('')
    expect(tabs.getByRole('link', { name: /hmm scoring/i })).toHaveAttribute('aria-current', 'page')
  })

  it('says HMM scoring is not available yet, before the box, and stays usable', () => {
    renderRoute('/hmmscore')

    const notice = main().getByText(/isn.t available on this site yet/i)
    expect(notice.compareDocumentPosition(sequenceBox())).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
    expect(sequenceBox()).toBeEnabled()
    expect(submitButton()).toBeEnabled()
  })

  it('fills the box with human APOE, in lines of 35, from the example', async () => {
    const { user } = renderRoute('/hmmscore')
    enter('MKV')

    await user.click(main().getByRole('button', { name: /use an example/i }))

    const lines = (sequenceBox() as HTMLTextAreaElement).value.split('\n')
    expect(lines.join('')).toHaveLength(317)
    expect(lines.join('')).toMatch(/^MKVLWAALLVTFLAGCQAKV/)
    expect(lines.slice(0, -1).every(line => line.length === 35)).toBe(true)
    expect(lines.at(-1)).toBe('NH')
  })
})

describe('the client checks', () => {
  it.each([
    ['nothing', ''],
    ['only a header', '>only a header'],
    ['a header and a lone stop', '>only a header\n*'],
    ['no letters', '.~'],
  ])('says there are no residues for %s, and sends nothing', async (_name, text) => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/hmmscore')
    enter(text)

    await user.click(submitButton())

    expect(sequenceBox()).toBeInvalid()
    expect(sequenceBox()).toHaveAccessibleDescription(/no residues/i)
    expect(bodies).toEqual([])
    expect(router.state.location.pathname).toBe('/hmmscore')
  })

  it.each([
    ['two sequences', '>one\nMKV\n>two\nMKV', /submit one protein/i],
    ['10,001 letters', letters(10_001), /longer than 10,000 residues|more than 10,000 residues/],
    ['9,998 letters and .*~', `${letters(9_998)}.*~`, /more than 10,000 residues/],
    ['M and a million spaces', `M${' '.repeat(1_000_000)}`, /1,000,000 characters/],
    ['a digit', 'MKV1L', /letters A to Z/],
    ['a dash', 'MKV-L', /letters A to Z/],
    ['a plus', 'MKV+L', /letters A to Z/],
    ['a ">" inside it', 'MKV>LW', /letters A to Z/],
    ['a letter outside ASCII', 'MKVÄL', /letters A to Z/],
  ])('refuses %s on the field, and sends nothing', async (_name, text, message) => {
    const bodies = serveStart()
    const { user } = renderRoute('/hmmscore')
    enter(text)

    await user.click(submitButton())

    expect(sequenceBox()).toBeInvalid()
    expect(sequenceBox()).toHaveAccessibleDescription(message)
    expect(bodies).toEqual([])
  })

  it('never quotes the sequence', async () => {
    const { user } = renderRoute('/hmmscore')
    enter('QWERTY1')

    await user.click(submitButton())

    expect(sequenceBox()).toBeInvalid()
    expect(sequenceBox()).not.toHaveAccessibleDescription(/QWERTY/)
  })

  it.each([
    ['the uncommon letters and a final stop', 'mkvbjouxz*\n'],
    ['an inner stop', 'MKV*L'],
    ['a dot', 'MKV.L'],
    ['an underscore', 'MKV_L'],
    ['a tilde', 'MKV~L'],
    ['two final stops', 'MKVL**'],
    ['10,000 letters and a final stop', `${letters(10_000)}*`],
  ])('sends %s as typed', async (_name, text) => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/hmmscore')
    enter(text)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'hmmscore', input: { sequence: text } }])
  })

  it('clears the error once the box is edited', async () => {
    const { user } = renderRoute('/hmmscore')
    await user.click(submitButton())
    expect(sequenceBox()).toBeInvalid()

    await user.type(sequenceBox(), 'M')

    expect(sequenceBox()).toBeValid()
  })
})

describe('submitting an hmmscore request', () => {
  it('sends the sequence as typed, and opens the job, headed as HMM scoring', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/hmmscore')
    await user.click(sequenceBox())
    await user.paste(VALID)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'hmmscore', input: { sequence: VALID } }])
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
    expect(main().getByRole('heading', { level: 2, name: /hmm scoring/i })).toBeVisible()
  })

  it('is disabled while the request is in flight', async () => {
    let release = () => {}
    serveStart(undefined, new Promise<void>(resolve => (release = resolve)))
    const { user, router } = renderRoute('/hmmscore')
    enter(VALID)

    await user.click(submitButton())

    await waitFor(() => expect(submitButton()).toBeDisabled())
    expect(router.state.location.pathname).toBe('/hmmscore')
    release()
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe("the API's validation errors", () => {
  it("shows a server's lower limit on the field, and keeps the sequence", async () => {
    serveValidationProblem({
      loc: ['body', 'hmmscore', 'input', 'sequence'],
      msg: 'The sequence has more than 5,000 residues.',
    })
    const text = letters(5_001)
    const { user, router } = renderRoute('/hmmscore')
    enter(text)

    await user.click(submitButton())

    await waitFor(() => expect(sequenceBox()).toBeInvalid())
    expect(sequenceBox()).toHaveAccessibleDescription(/more than 5,000 residues/)
    expect(sequenceBox()).toHaveValue(text)
    expect(router.state.location.pathname).toBe('/hmmscore')
  })

  it('shows an error on no field with the form', async () => {
    serveValidationProblem({ loc: ['body', 'hmmscore', 'input', 'opType'], msg: 'Extra input.' })
    const { user } = renderRoute('/hmmscore')
    enter(VALID)

    await user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/extra input/i)
    expect(sequenceBox()).toBeValid()
  })

  it("clears the API's error when the box is edited, and opens the job once accepted", async () => {
    serveValidationProblem({ loc: ['body', 'hmmscore', 'input', 'sequence'], msg: 'Refused.' })
    const { user, router } = renderRoute('/hmmscore')
    enter(VALID)
    await user.click(submitButton())
    await waitFor(() => expect(sequenceBox()).toBeInvalid())

    await user.type(sequenceBox(), 'L')

    expect(sequenceBox()).toBeValid()
    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe('when the job is not started', () => {
  it("says HMM scoring isn't available yet on the API's 501, in fixed text", async () => {
    const bodies = serveProblem(501, problem(501, 'Not Implemented'))
    const rendered = renderRoute('/hmmscore')
    enter(VALID)

    await rendered.user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/hmm scoring isn.t available yet/i)
    expect(bodies).toHaveLength(1)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(STATUS_CODES)
    await keptAndUsable(rendered, VALID)
  })

  it('says HMM scoring is busy, and when to try again, on a 503 with Retry-After', async () => {
    serveProblem(503, problem(503, 'Service Unavailable'), { 'Retry-After': '30' })
    const rendered = renderRoute('/hmmscore')
    enter(VALID)

    await rendered.user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/hmm scoring is busy/i)
    expect(alert).toHaveTextContent(/try again in about 30 seconds/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(STATUS_CODES)
    await keptAndUsable(rendered, VALID)
  })

  it('says to try again in a few minutes on a busy 503 without Retry-After', async () => {
    serveProblem(503, problem(503, 'Service Unavailable'))
    const { user } = renderRoute('/hmmscore')
    enter(VALID)

    await user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/try again in a few minutes/i)
  })

  it('says the job could not be started on a 500, with no status or build details', async () => {
    serveProblem(500, problem(500, 'Internal Server Error'))
    const rendered = renderRoute('/hmmscore')
    enter(VALID)

    await rendered.user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/couldn.t be started/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(STATUS_CODES)
    await keptAndUsable(rendered, VALID)
  })

  it.each([
    ['the network fails', () => HttpResponse.error()],
    [
      'a 501 has no problem details',
      () =>
        new HttpResponse('Not Implemented', {
          status: 501,
          headers: { 'Content-Type': 'text/html' },
        }),
    ],
  ])("says the scoring service can't be reached when %s", async (_name, answer) => {
    server.use(http.post('/api/v1/jobs', answer))
    const rendered = renderRoute('/hmmscore')
    enter(VALID)

    await rendered.user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/can.t be reached/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    await keptAndUsable(rendered, VALID)
  })
})

describe('after submitting', () => {
  it('reopens the form filled in as typed from "Edit and resubmit", and says so', async () => {
    serveStart()
    const { user, router } = renderRoute('/hmmscore')
    enter(VALID)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)

    await user.click(main().getByRole('link', { name: /edit and resubmit/i }))

    expect(router.state.location.pathname).toBe('/hmmscore')
    expect(main().getByText(/filled in from your earlier job/i)).toBeInTheDocument()
    expect(sequenceBox()).toHaveValue(VALID)
  })

  it('drops the note when the example replaces the edited input', async () => {
    serveStart()
    const { user } = renderRoute('/hmmscore')
    enter(VALID)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
    await user.click(main().getByRole('link', { name: /edit and resubmit/i }))

    await user.click(main().getByRole('button', { name: /use an example/i }))

    expect(main().queryByText(/filled in from your earlier job/i)).not.toBeInTheDocument()
    expect(sequenceBox()).not.toHaveValue(VALID)
  })

  it('opens an empty form from the new HMM scoring search link', async () => {
    serveStart()
    const { user } = renderRoute('/hmmscore')
    enter(VALID)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)

    await user.click(main().getByRole('link', { name: /new hmm scoring search/i }))

    expect(sequenceBox()).toHaveValue('')
    expect(main().queryByText(/filled in from your earlier job/i)).not.toBeInTheDocument()
  })
})
