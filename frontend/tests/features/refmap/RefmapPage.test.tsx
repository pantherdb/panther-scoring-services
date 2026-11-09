import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { organisms as mockedOrganisms } from '@/mocks/data/organisms'
import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/
const PROBLEM = { 'Content-Type': 'application/problem+json' }
const JOB_PATH = /^\/jobs\/[0-9a-f-]{36}$/

const IDS = 'P04217\np04217, P01023\tA1BG\nP04217-2'
const SENT_IDS = ['P04217', 'p04217', 'P01023', 'P04217-2']

const ENDPU = 'Endocarpon pusillum (ENDPU)'

type User = ReturnType<typeof renderRoute>['user']

function main() {
  return within(screen.getByRole('main'))
}

function idsBox() {
  return main().getByRole('textbox', { name: /protein ids/i })
}

// The organism selector, or the code box when the list can't be loaded: the same label. By
// role, since the selector's open list of options has that label too.
function organismBox() {
  return (
    main().queryByRole('combobox', { name: /organism/i }) ??
    main().getByRole('textbox', { name: /organism/i })
  )
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

// The selector is enabled once the mocked list has loaded. Waits for the selector itself: after a
// retry, the code box is still shown, and enabled, until the list arrives.
async function organismsLoaded() {
  await waitFor(() => expect(main().getByRole('combobox', { name: /organism/i })).toBeEnabled())
}

// Clears the selector's text and types `text` in it. A click leaves the chosen organism's label
// in the box, so typing alone would add to it.
async function search(user: User, text: string) {
  await organismsLoaded()
  await user.click(organismBox())
  await user.clear(organismBox())
  await user.type(organismBox(), text)
}

async function optionNames() {
  return (await screen.findAllByRole('option')).map(option => option.textContent)
}

async function chooseOrganism(user: User, text = 'pusill', option = ENDPU) {
  await search(user, text)
  await user.click(await screen.findByRole('option', { name: option }))
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

function serveOrganismsFailure() {
  server.use(
    http.get('/api/v1/refmap/organisms', () =>
      HttpResponse.json(
        { type: 'about:blank', title: 'x', status: 500, detail: 'at /opt/app :8000' },
        { status: 500, headers: PROBLEM }
      )
    )
  )
}

async function fallbackShown() {
  expect(await main().findByRole('button', { name: /organisms again/i })).toBeInTheDocument()
}

// Fills the form with a valid input. Paste, not type: typing a long list is slow.
async function fillValid(user: User) {
  await user.click(idsBox())
  await user.paste(IDS)
  await chooseOrganism(user)
}

describe('the refmap form', () => {
  it('opens from the home page, with empty boxes and no organism chosen', async () => {
    const { user, router } = renderRoute('/')

    await user.click(main().getByRole('link', { name: /map protein ids/i }))

    expect(router.state.location.pathname).toBe('/refmap')
    expect(main().getByRole('heading', { level: 2, name: /protein id mapping/i })).toBeVisible()
    expect(idsBox()).toHaveValue('')
    await organismsLoaded()
    expect(organismBox()).toHaveValue('')
    expect(main().getByText(/no ids yet/i)).toBeInTheDocument()
    expect(submitButton()).toBeEnabled()
  })

  it("fills both fields with the example, six of ENDPU's IDs and ENDPU", async () => {
    const { user } = renderRoute('/refmap')
    await chooseOrganism(user, 'eco57', 'Escherichia coli O157:H7 (ECO57)')

    await user.click(exampleButton())

    expect((idsBox() as HTMLTextAreaElement).value.split('\n')).toEqual([
      'U1G4Q5',
      'U1GCA1',
      'U1HRR6',
      'U1GLV9',
      'U1GJ40',
      'U1HQ27',
    ])
    expect(organismBox()).toHaveValue(ENDPU)
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

describe('the organism selector', () => {
  it('offers each organism the API lists, by name and code, sorted by name', async () => {
    const { user } = renderRoute('/refmap')
    await organismsLoaded()

    await user.click(organismBox())

    const expected = mockedOrganisms
      .map(({ code, name }) => `${name} (${code})`)
      .sort((a, b) => a.localeCompare(b, 'en'))
    expect(await optionNames()).toEqual(expected)
  })

  it('finds organisms by part of a name, in any case, and chooses one', async () => {
    const { user } = renderRoute('/refmap')

    await search(user, 'PUSILL')

    expect(await optionNames()).toEqual([ENDPU, 'Micromonas pusilla (MICPC)'])
    await user.click(screen.getByRole('option', { name: ENDPU }))
    expect(organismBox()).toHaveValue(ENDPU)
  })

  it('finds an organism by its code, in any case', async () => {
    const { user } = renderRoute('/refmap')

    await search(user, 'eco57')

    expect(await optionNames()).toEqual(['Escherichia coli O157:H7 (ECO57)'])
  })

  it('says when no organism matches', async () => {
    const { user } = renderRoute('/refmap')

    await search(user, 'xyz')

    expect(screen.queryAllByRole('option')).toEqual([])
    expect(main().getByText(/no organism matches/i)).toBeInTheDocument()
  })

  it("sends the chosen organism's code", async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'ENDPU', ids: SENT_IDS } }])
  })

  it('works with the keyboard alone', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await user.click(idsBox())
    await user.paste(IDS)
    await organismsLoaded()

    await user.tab()
    await user.tab()
    expect(organismBox()).toHaveFocus()
    await user.keyboard('araneus')
    await user.keyboard('{ArrowDown}{Enter}')
    expect(organismBox()).toHaveValue('Araneus ventricosus (ARAVE)')
    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([
      expect.objectContaining({ input: expect.objectContaining({ organism: 'ARAVE' }) }),
    ])
  })

  it('says the organisms are loading until the list arrives, and the IDs can be filled', async () => {
    let release = () => {}
    const gate = new Promise<void>(resolve => (release = resolve))
    server.use(
      http.get('/api/v1/refmap/organisms', async () => {
        await gate
        return HttpResponse.json(mockedOrganisms)
      })
    )
    const { user } = renderRoute('/refmap')

    expect(organismBox()).toBeDisabled()
    expect(organismBox()).toHaveAttribute('placeholder', expect.stringMatching(/loading/i))
    await user.click(idsBox())
    await user.paste(IDS)
    expect(idsBox()).toHaveValue(IDS)

    release()
    await organismsLoaded()
  })
})

describe('when the organism list can’t be loaded', () => {
  function retryButton() {
    return main().getByRole('button', { name: /load the list of organisms again/i })
  }

  it('offers an empty box for the code, says why in fixed text, and offers to retry', async () => {
    serveOrganismsFailure()
    renderRoute('/refmap')

    await fallbackShown()

    expect(organismBox()).toHaveRole('textbox')
    expect(organismBox()).toHaveValue('')
    expect(organismBox()).toBeEnabled()
    expect(organismBox()).toHaveAccessibleDescription(/couldn.t be loaded/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(/500/)
  })

  it.each([
    ['as typed', 'ENDPU'],
    ['trimmed', ' ENDPU '],
  ])('sends a typed code, %s', async (_name, typed) => {
    serveOrganismsFailure()
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await fallbackShown()
    await user.click(idsBox())
    await user.paste(IDS)
    await user.type(organismBox(), typed)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'ENDPU', ids: SENT_IDS } }])
  })

  it.each([
    ['empty', '', /species code/i],
    ['lower case', 'endpu', /1 to 5 upper-case letters or digits/],
    ['too long', 'ENDOCARPON', /1 to 5 upper-case letters or digits/],
    ['a path', '../x', /1 to 5 upper-case letters or digits/],
  ])(
    'checks the shape of a typed code: %s is refused on its field only, unquoted',
    async (_name, text, error) => {
      serveOrganismsFailure()
      const bodies = serveStart()
      const { user } = renderRoute('/refmap')
      await fallbackShown()
      await user.click(idsBox())
      await user.paste(IDS)
      if (text) await user.type(organismBox(), text)

      await user.click(submitButton())

      expect(organismBox()).toBeInvalid()
      expect(organismBox()).toHaveAccessibleDescription(error)
      if (text) {
        expect(organismBox()).not.toHaveAccessibleDescription(
          new RegExp(text.replaceAll('.', '\\.'))
        )
      }
      expect(idsBox()).toBeValid()
      expect(bodies).toEqual([])
    }
  )

  it('brings the selector back on a retry, keeping the typed organism', async () => {
    serveOrganismsFailure()
    const { user } = renderRoute('/refmap')
    await fallbackShown()
    await user.type(organismBox(), 'ENDPU')
    server.resetHandlers()

    await user.click(retryButton())

    await waitFor(() => expect(organismBox()).toHaveValue(ENDPU))
    expect(organismBox()).toHaveRole('combobox')
    expect(main().queryByRole('button', { name: /organisms again/i })).toBeNull()
  })

  it('refuses a typed code the list turns out not to have, such as HUMAN, and sends nothing', async () => {
    serveOrganismsFailure()
    const { user } = renderRoute('/refmap')
    await fallbackShown()
    await user.click(idsBox())
    await user.paste(IDS)
    await user.type(organismBox(), 'HUMAN')
    server.resetHandlers()
    const bodies = serveStart()
    await user.click(retryButton())
    await organismsLoaded()

    await user.click(submitButton())

    expect(organismBox()).toBeInvalid()
    expect(organismBox()).toHaveAccessibleDescription(/from the list/i)
    expect(organismBox()).not.toHaveAccessibleDescription(/HUMAN/)
    expect(organismBox()).toHaveValue('')
    expect(bodies).toEqual([])
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
    await chooseOrganism(user)
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'ENDPU', ids: SENT_IDS } }])
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
  it('shows an error on each empty field and sends nothing', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await organismsLoaded()

    await user.click(submitButton())

    expect(idsBox()).toBeInvalid()
    expect(organismBox()).toBeInvalid()
    expect(idsBox()).toHaveAccessibleDescription(/at least one id/i)
    expect(organismBox()).toHaveAccessibleDescription(/choose an organism/i)
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
    await chooseOrganism(user)

    await user.click(submitButton())

    expect(idsBox()).toBeInvalid()
    expect(idsBox()).toHaveAccessibleDescription(error)
    expect(organismBox()).toBeValid()
    expect(bodies).toEqual([])
  })

  it("clears a field's error once it is edited", async () => {
    const { user } = renderRoute('/refmap')
    await organismsLoaded()
    await user.click(submitButton())

    await chooseOrganism(user)

    expect(organismBox()).toBeValid()
    expect(idsBox()).toBeInvalid()
  })
})

describe('submitting a refmap request', () => {
  it('sends the IDs as split and the organism, and opens the job', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'ENDPU', ids: SENT_IDS } }])
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
    await chooseOrganism(user)

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([{ service: 'refmap', input: { organism: 'ENDPU', ids } }])
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
    expect(organismBox()).toHaveValue(ENDPU)
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

    await chooseOrganism(user, 'eco57', 'Escherichia coli O157:H7 (ECO57)')

    expect(organismBox()).toBeValid()
    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe('when the job is not started', () => {
  it.each([
    [
      '500',
      500,
      { type: 'about:blank', title: 'Internal Server Error', status: 500, detail: 'at /opt/app' },
    ],
    [
      '501 from an older API',
      501,
      { type: 'about:blank', title: 'Not Implemented', status: 501, detail: 'Not yet.' },
    ],
  ])(
    'says the job could not be started on a %s, with no status or build details, and keeps the input',
    async (_name, status, body) => {
      const bodies = serveProblem(status, body)
      const { user, router } = renderRoute('/refmap')
      await fillValid(user)

      await user.click(submitButton())

      const alert = await main().findByRole('alert')
      expect(alert).toHaveTextContent(/couldn.t be started/i)
      expect(bodies).toHaveLength(1)
      expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
      expect(screen.getByRole('main').textContent).not.toMatch(
        /50[01]|internal server error|not implemented/i
      )
      expect(router.state.location.pathname).toBe('/refmap')
      expect(idsBox()).toHaveValue(IDS)
      expect(organismBox()).toHaveValue(ENDPU)
      expect(submitButton()).toBeEnabled()

      serveStart()
      await user.click(submitButton())
      await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    }
  )

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
      expect(organismBox()).toHaveValue(ENDPU)
      expect(submitButton()).toBeEnabled()

      serveStart()
      await user.click(submitButton())
      await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    }
  )
})

describe('after submitting', () => {
  it('reopens the form filled in as typed from "Edit and resubmit", and says so', async () => {
    serveStart()
    const { user, router } = renderRoute('/refmap')
    await fillValid(user)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)

    await user.click(main().getByRole('link', { name: /edit and resubmit/i }))

    expect(router.state.location.pathname).toBe('/refmap')
    expect(main().getByText(/filled in from your earlier job/i)).toBeInTheDocument()
    expect(idsBox()).toHaveValue(IDS)
    expect(organismBox()).toHaveValue(ENDPU)
  })

  it('starts an empty form, without the note, from the ID mapping tab on an edited form', async () => {
    serveStart()
    const { user } = renderRoute('/refmap')
    await fillValid(user)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
    await user.click(main().getByRole('link', { name: /edit and resubmit/i }))
    expect(main().getByText(/filled in from your earlier job/i)).toBeInTheDocument()

    await user.click(
      within(screen.getByRole('navigation', { name: /services/i })).getByRole('link', {
        name: /id mapping/i,
      })
    )

    expect(main().queryByText(/filled in from your earlier job/i)).not.toBeInTheDocument()
    expect(idsBox()).toHaveValue('')
    expect(organismBox()).toHaveValue('')
  })

  it('drops the note when the example replaces the edited input', async () => {
    serveStart()
    const { user } = renderRoute('/refmap')
    await fillValid(user)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
    await user.click(main().getByRole('link', { name: /edit and resubmit/i }))

    await user.click(exampleButton())

    expect(main().queryByText(/filled in from your earlier job/i)).not.toBeInTheDocument()
    expect(idsBox()).not.toHaveValue(IDS)
  })

  it('opens an empty form from "New ID mapping"', async () => {
    serveStart()
    const { user } = renderRoute('/refmap')
    await fillValid(user)
    await user.click(submitButton())
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)

    await user.click(main().getByRole('link', { name: /new id mapping/i }))

    expect(idsBox()).toHaveValue('')
    expect(organismBox()).toHaveValue('')
  })
})
