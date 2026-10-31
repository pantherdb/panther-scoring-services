import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/
const PROBLEM = { 'Content-Type': 'application/problem+json' }
const JOB_PATH = /^\/jobs\/[0-9a-f-]{36}$/

const IDS = 'P04217\np04217, P01023\tA1BG\nP04217-2'
const SENT_IDS = ['P04217', 'p04217', 'P01023', 'P04217-2']

type User = ReturnType<typeof renderRoute>['user']

function main() {
  return within(screen.getByRole('main'))
}

function idsBox() {
  return main().getByRole('textbox', { name: /protein ids/i })
}

function organismBox() {
  return main().getByRole('textbox', { name: /organism/i })
}

function fileInput() {
  return main().getByLabelText(/text file of protein ids/i)
}

function submitButton() {
  return main().getByRole('button', { name: /map ids/i })
}

function exampleButton() {
  return main().getByRole('button', { name: /use an example/i })
}

// Answers POST /jobs with `answer`, or, by default, as the mocked API does (a queued refmap
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
      const job = createJob('refmap', SENT_IDS)
      return HttpResponse.json(job, {
        status: 202,
        headers: { Location: `/api/v1/jobs/${job.id}` },
      })
    })
  )
  return bodies
}

function serveProblem(status: number, body: object) {
  return serveStart(() => HttpResponse.json(body, { status, headers: PROBLEM }))
}

function serveValidationProblem(...errors: { loc: (string | number)[]; msg: string }[]) {
  return serveProblem(422, {
    type: 'about:blank',
    title: 'Unprocessable Content',
    status: 422,
    detail: 'Request validation failed',
    errors: errors.map(error => ({ ...error, type: 'value_error' })),
  })
}

const NOT_IMPLEMENTED = {
  type: 'about:blank',
  title: 'Not Implemented',
  status: 501,
  detail: "refmap ID mapping isn't available yet.",
}

// Fills the form with a valid input. Paste, not type: typing a long list is slow.
async function fillValid(user: User) {
  await user.click(idsBox())
  await user.paste(IDS)
  await user.type(organismBox(), 'HUMAN')
}

describe('the refmap form', () => {
  it('opens from the home page, with empty boxes', async () => {
    const { user, router } = renderRoute('/')

    await user.click(main().getByRole('link', { name: /map protein ids/i }))

    expect(router.state.location.pathname).toBe('/refmap')
    expect(main().getByRole('heading', { level: 2, name: /protein id mapping/i })).toBeVisible()
    expect(idsBox()).toHaveValue('')
    expect(organismBox()).toHaveValue('')
    expect(main().getByText(/no ids yet/i)).toBeInTheDocument()
    expect(submitButton()).toBeEnabled()
  })

  it('fills both boxes with the example, six human accessions and HUMAN', async () => {
    const { user } = renderRoute('/refmap')
    await user.type(organismBox(), 'MOUSE')

    await user.click(exampleButton())

    expect((idsBox() as HTMLTextAreaElement).value.split('\n')).toEqual([
      'P04217',
      'P01023',
      'P02649',
      'P04637',
      'P38398',
      'P00533',
    ])
    expect(organismBox()).toHaveValue('HUMAN')
    expect(await main().findByText(/^6 IDs will be sent\.$/)).toBeInTheDocument()
  })

  it('says how IDs are separated, and that case matters', () => {
    renderRoute('/refmap')

    expect(idsBox()).toHaveAccessibleDescription(/one per line.*spaces or commas/i)
    expect(idsBox()).toHaveAccessibleDescription(/case matters/i)
    expect(idsBox()).toHaveAccessibleDescription(/only the first column/i)
  })

  it('counts the IDs that will be sent, and the lines whose other columns are left out', async () => {
    const { user } = renderRoute('/refmap')

    await user.click(idsBox())
    await user.paste(IDS)

    expect(await main().findByText(/^4 IDs will be sent\./)).toHaveTextContent(
      /first column was read on 1 line/i
    )
    await user.clear(idsBox())
    await user.type(idsBox(), 'P04217')
    expect(await main().findByText(/^1 ID will be sent\.$/)).toBeInTheDocument()
  })
})

describe('loading a text file', () => {
  it("puts the file's contents in the box, read in the browser, and counts them", async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    const file = new File([IDS], 'ids.tsv', { type: 'text/tab-separated-values' })

    await user.upload(fileInput(), file)

    await waitFor(() => expect(idsBox()).toHaveValue(IDS))
    expect(await main().findByText(/^4 IDs will be sent\./)).toBeInTheDocument()
    expect(bodies).toEqual([])
    await user.type(organismBox(), 'HUMAN')
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'HUMAN', ids: SENT_IDS } }])
  })

  it('replaces what was in the box, and clears its error', async () => {
    const { user } = renderRoute('/refmap')
    await user.click(submitButton())
    expect(idsBox()).toBeInvalid()

    await user.upload(fileInput(), new File(['Q9Y6K9'], 'ids.txt', { type: 'text/plain' }))

    await waitFor(() => expect(idsBox()).toHaveValue('Q9Y6K9'))
    expect(idsBox()).toBeValid()
  })

  it('refuses a file over 10 MB on the IDs field, and keeps the box', async () => {
    const { user } = renderRoute('/refmap')
    await user.click(idsBox())
    await user.paste('P04217')
    const file = new File(['P'.repeat(10 * 1024 * 1024 + 1)], 'big.txt', { type: 'text/plain' })

    await user.upload(fileInput(), file)

    await waitFor(() => expect(idsBox()).toBeInvalid())
    expect(idsBox()).toHaveAccessibleDescription(/larger than 10 MB/)
    expect(idsBox()).toHaveValue('P04217')
  })
})

describe('the client checks', () => {
  it('shows an error on each empty box and sends nothing', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')

    await user.click(submitButton())

    expect(idsBox()).toBeInvalid()
    expect(organismBox()).toBeInvalid()
    expect(idsBox()).toHaveAccessibleDescription(/at least one id/i)
    expect(organismBox()).toHaveAccessibleDescription(/species code/i)
    expect(bodies).toEqual([])
    expect(router.state.location.pathname).toBe('/refmap')
  })

  it.each([
    ['too many IDs', 'P1 '.repeat(100_001), /at most 100,000 IDs/],
    ['an ID that is too long', `P04217 ${'A'.repeat(65)}`, /ID 2 \(A{24}…, line 1\).*64/],
    [
      'IDs that are not printable ASCII, naming them',
      'P04217\nP0é4217\nP04217 Q–1',
      /IDs 2 \(P0é4217, line 2\), 4 \(Q–1, line 3\)/,
    ],
  ])('shows an error for %s, on the IDs only, and sends nothing', async (_name, text, error) => {
    const bodies = serveStart()
    const { user } = renderRoute('/refmap')
    await user.click(idsBox())
    await user.paste(text)
    await user.type(organismBox(), 'HUMAN')

    await user.click(submitButton())

    expect(idsBox()).toBeInvalid()
    expect(idsBox()).toHaveAccessibleDescription(error)
    expect(organismBox()).toBeValid()
    expect(bodies).toEqual([])
  })

  it.each([
    ['lower case', 'human'],
    ['too long', 'HOMOSAPIENS'],
    ['a path', '../x'],
  ])('refuses an organism in %s, on its field only', async (_name, organism) => {
    const bodies = serveStart()
    const { user } = renderRoute('/refmap')
    await user.click(exampleButton())
    await user.clear(organismBox())
    await user.type(organismBox(), organism)

    await user.click(submitButton())

    expect(organismBox()).toBeInvalid()
    expect(organismBox()).toHaveAccessibleDescription(/1 to 5 upper-case letters or digits/)
    expect(organismBox()).not.toHaveAccessibleDescription(new RegExp(organism.replace('.', '\\.')))
    expect(idsBox()).toBeValid()
    expect(bodies).toEqual([])
  })

  it("clears a field's error once it is edited", async () => {
    const { user } = renderRoute('/refmap')
    await user.click(submitButton())

    await user.type(organismBox(), 'H')

    expect(organismBox()).toBeValid()
    expect(idsBox()).toBeInvalid()
  })
})

describe('submitting a refmap request', () => {
  it('sends the IDs as split and the organism trimmed, and opens the job', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await user.click(idsBox())
    await user.paste(IDS)
    await user.type(organismBox(), ' HUMAN ')

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'HUMAN', ids: SENT_IDS } }])
    // The status first: the form's own heading reads the same as the job page's.
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
    expect(main().getByRole('heading', { level: 2, name: /protein id mapping/i })).toBeVisible()
  })

  it('sends 100,000 IDs', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    const ids = Array.from({ length: 100_000 }, (_, i) => `P${i}`)
    await user.click(idsBox())
    await user.paste(ids.join('\n'))
    await user.type(organismBox(), 'HUMAN')

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'HUMAN', ids } }])
  })

  it('is disabled while the request is in flight', async () => {
    let release = () => {}
    serveStart(undefined, new Promise<void>(resolve => (release = resolve)))
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(submitButton()).toBeDisabled())
    expect(router.state.location.pathname).toBe('/refmap')
    release()
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe("the API's validation errors", () => {
  it("shows a 422's msg on the field its loc names, keeps the input, and stays", async () => {
    serveValidationProblem({
      loc: ['body', 'refmap', 'input', 'organism'],
      msg: 'The API refuses this organism.',
    })
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(organismBox()).toBeInvalid())
    expect(organismBox()).toHaveAccessibleDescription(/the api refuses this organism/i)
    expect(idsBox()).toBeValid()
    expect(idsBox()).toHaveValue(IDS)
    expect(organismBox()).toHaveValue('HUMAN')
    expect(router.state.location.pathname).toBe('/refmap')
  })

  it("names the ID a 422's error is about by place, line and as sent", async () => {
    serveValidationProblem({
      loc: ['body', 'refmap', 'input', 'ids', 2],
      msg: 'The API refuses this ID.',
    })
    const { user } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(idsBox()).toBeInvalid())
    expect(idsBox()).toHaveAccessibleDescription(
      /ID 3 \(P01023, line 2\): the api refuses this id/i
    )
    expect(organismBox()).toBeValid()
  })

  it('shows an error on no field of the form with the form', async () => {
    serveValidationProblem({ loc: ['body', 'refmap', 'input', 'fileContents'], msg: 'Extra.' })
    const { user } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/extra/i)
    expect(idsBox()).toBeValid()
    expect(organismBox()).toBeValid()
  })

  it("clears the API's error when the field is edited, and opens the job once accepted", async () => {
    serveValidationProblem({ loc: ['body', 'refmap', 'input', 'organism'], msg: 'Refused.' })
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)
    await user.click(submitButton())
    await waitFor(() => expect(organismBox()).toBeInvalid())

    await user.clear(organismBox())
    await user.type(organismBox(), 'MOUSE')

    expect(organismBox()).toBeValid()
    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe('when the job is not started', () => {
  it("says on a 501 that mapping isn't available yet, keeps the input, and stays", async () => {
    const bodies = serveProblem(501, NOT_IMPLEMENTED)
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/isn.t available yet/i)
    expect(alert).not.toHaveTextContent(/couldn.t be started/i)
    expect(bodies).toHaveLength(1)
    expect(idsBox()).toHaveValue(IDS)
    expect(organismBox()).toHaveValue('HUMAN')
    expect(router.state.location.pathname).toBe('/refmap')
    expect(screen.getByRole('main').textContent).not.toMatch(/501|not implemented/i)
    expect(submitButton()).toBeEnabled()

    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })

  it('says the job could not be started on a 500, with no status or build details', async () => {
    serveProblem(500, {
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'at /opt/app',
    })
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/couldn.t be started/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(/500|internal server error/i)
    expect(router.state.location.pathname).toBe('/refmap')

    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })

  it.each([
    ['the network fails', () => HttpResponse.error()],
    [
      'the dev proxy has no API behind it',
      () => new HttpResponse(null, { status: 500, headers: { 'Content-Type': 'text/plain' } }),
    ],
  ])(
    "says the scoring service can't be reached when %s, and keeps the input",
    async (_, answer) => {
      server.use(http.post('/api/v1/jobs', answer))
      const { user, router } = renderRoute('/refmap')
      await fillValid(user)

      await user.click(submitButton())

      const alert = await main().findByRole('alert')
      expect(alert).toHaveTextContent(/can.t be reached/i)
      expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
      expect(router.state.location.pathname).toBe('/refmap')
      expect(idsBox()).toHaveValue(IDS)
      expect(submitButton()).toBeEnabled()

      serveStart()
      await user.click(submitButton())
      await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    }
  )
})
