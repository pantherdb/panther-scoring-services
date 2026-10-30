import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { csnpUnavailable } from '@/mocks/data/jobs'
import { createJob } from '@/mocks/jobs'

import { server } from '../../mocks/server'
import { renderRoute } from '../../utils/render'

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx |\/usr\/|\/opt\/|[A-Z]:\\/
const PROBLEM = { 'Content-Type': 'application/problem+json' }
const JOB_PATH = /^\/jobs\/[0-9a-f-]{36}$/

const SEQUENCE = '>sp|P02649|APOE_HUMAN\nMKVLWAALLV\nTFLAGCQAKV\n'

function main() {
  return within(screen.getByRole('main'))
}

function sequenceBox() {
  return main().getByLabelText(/protein sequence/i)
}

function substitutionsBox() {
  return main().getByLabelText(/substitutions/i)
}

function speciesBox() {
  return main().getByLabelText(/species/i)
}

function submitButton() {
  return main().getByRole('button', { name: /score substitutions/i })
}

type Answer = (() => Response) | undefined

// Answers POST /jobs with `answer`, or, by default, as the mocked API does (a queued csnp
// job), after `gate` resolves. Records each request body.
function serveStart(answer: Answer = undefined, gate: Promise<void> = Promise.resolve()) {
  const bodies: unknown[] = []
  server.use(
    http.post('/api/v1/jobs', async ({ request }) => {
      bodies.push(await request.json())
      await gate
      if (answer) return answer()
      const job = createJob('csnp')
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

// Fills the form with a valid input. Paste, not type: typing a long sequence is slow.
async function fillValid(user: ReturnType<typeof renderRoute>['user']) {
  await user.click(sequenceBox())
  await user.paste(SEQUENCE)
  await user.click(substitutionsBox())
  await user.paste('L4P c13r\nG12V')
}

describe('the cSNP form', () => {
  it('opens from the home page, with empty boxes and the species HUMAN', async () => {
    const { user, router } = renderRoute('/')

    await user.click(main().getByRole('link', { name: /score coding snps/i }))

    expect(router.state.location.pathname).toBe('/csnp')
    expect(sequenceBox()).toHaveValue('')
    expect(substitutionsBox()).toHaveValue('')
    expect(speciesBox()).toHaveValue('HUMAN')
    expect(submitButton()).toBeEnabled()
  })

  it("fills every box with the legacy website's example", async () => {
    const { user } = renderRoute('/csnp')
    await user.type(speciesBox(), 'X')

    await user.click(main().getByRole('button', { name: /use an example/i }))

    expect((sequenceBox() as HTMLTextAreaElement).value.replace(/\s/g, '')).toMatch(
      /^MKVLWAALLVTFLAGCQAKV.*PVPSDNH$/
    )
    expect((substitutionsBox() as HTMLTextAreaElement).value.split(/\s+/)).toEqual([
      'L46P',
      'C130R',
      'R163C',
      'R176C',
    ])
    expect(speciesBox()).toHaveValue('HUMAN')
  })
})

describe('the client checks', () => {
  it('shows an error on each empty field and sends nothing', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/csnp')
    await user.clear(speciesBox())

    await user.click(submitButton())

    for (const box of [sequenceBox(), substitutionsBox(), speciesBox()]) {
      expect(box).toBeInvalid()
    }
    expect(sequenceBox()).toHaveAccessibleDescription(/enter a protein sequence/i)
    expect(substitutionsBox()).toHaveAccessibleDescription(/at least one substitution/i)
    expect(speciesBox()).toHaveAccessibleDescription(/species code/i)
    expect(bodies).toEqual([])
    expect(router.state.location.pathname).toBe('/csnp')
  })

  it.each([
    ['two sequences', sequenceBox, '>one\nMKV\n>two\nMKV', /more than one sequence/i],
    ['too many residues', sequenceBox, 'M'.repeat(50_001), /50,000 residues/],
    ['too many substitutions', substitutionsBox, 'L1P '.repeat(1_001), /1,000 substitutions/],
    ['a token that is too long', substitutionsBox, `L1P ${'L'.repeat(33)}`, /substitution 2 .*32/i],
    [
      'tokens that are not substitutions, naming them',
      substitutionsBox,
      'L46P XYZ\nC130R G12|',
      /substitutions 2 \(XYZ\), 4 \(G12\|\)/i,
    ],
    ['lower case', speciesBox, 'human', /upper-case/i],
    ['too long', speciesBox, 'HOMOSAPIENS', /upper-case/i],
  ])(
    'shows an error for %s, on its field only, and sends nothing',
    async (_name, box, text, error) => {
      const bodies = serveStart()
      const { user } = renderRoute('/csnp')
      await user.click(main().getByRole('button', { name: /use an example/i }))
      await user.clear(box())
      await user.click(box())
      await user.paste(text)

      await user.click(submitButton())

      expect(box()).toBeInvalid()
      expect(box()).toHaveAccessibleDescription(error)
      const others = [sequenceBox(), substitutionsBox(), speciesBox()].filter(b => b !== box())
      for (const other of others) expect(other).toBeValid()
      expect(bodies).toEqual([])
    }
  )

  it('clears a field’s error once it is edited', async () => {
    const { user } = renderRoute('/csnp')
    await user.click(submitButton())
    expect(sequenceBox()).toBeInvalid()

    await user.type(sequenceBox(), 'M')

    expect(sequenceBox()).toBeValid()
    expect(substitutionsBox()).toBeInvalid()
  })
})

describe('submitting a cSNP request', () => {
  it('sends the sequence as typed, the substitutions split, the species trimmed, and opens the job', async () => {
    const bodies = serveStart()
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)
    await user.clear(speciesBox())
    await user.type(speciesBox(), 'PLAF7 ')

    await user.click(submitButton())

    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
    expect(bodies).toEqual([
      {
        service: 'csnp',
        input: { sequence: SEQUENCE, substitutions: ['L4P', 'c13r', 'G12V'], species: 'PLAF7' },
      },
    ])
    expect(await main().findByRole('status')).toHaveTextContent(/queued/i)
  })

  it('is disabled while the request is in flight', async () => {
    let release = () => {}
    serveStart(undefined, new Promise<void>(resolve => (release = resolve)))
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(submitButton()).toBeDisabled())
    expect(router.state.location.pathname).toBe('/csnp')
    release()
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe("the API's validation errors", () => {
  it("shows a 422's msg on the field its loc names, keeps the input, and stays", async () => {
    serveValidationProblem({
      loc: ['body', 'csnp', 'input', 'species'],
      msg: 'The API refuses this species.',
    })
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(speciesBox()).toBeInvalid())
    expect(speciesBox()).toHaveAccessibleDescription(/the api refuses this species/i)
    expect(sequenceBox()).toBeValid()
    expect(sequenceBox()).toHaveValue(SEQUENCE)
    expect(substitutionsBox()).toHaveValue('L4P c13r\nG12V')
    expect(speciesBox()).toHaveValue('HUMAN')
    expect(router.state.location.pathname).toBe('/csnp')
  })

  it("names the substitution a 422's error is about, counted from 1", async () => {
    serveValidationProblem({
      loc: ['body', 'csnp', 'input', 'substitutions', 2],
      msg: 'The API refuses this token.',
    })
    const { user } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    await waitFor(() => expect(substitutionsBox()).toBeInvalid())
    expect(substitutionsBox()).toHaveAccessibleDescription(
      /substitution 3 \(G12V\): the api refuses this token/i
    )
  })

  it('shows an error on no field of the form with the form', async () => {
    serveValidationProblem({ loc: ['body', 'csnp', 'input', 'organism'], msg: 'Extra inputs.' })
    const { user } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/extra inputs/i)
    for (const box of [sequenceBox(), substitutionsBox(), speciesBox()]) {
      expect(box).toBeValid()
    }
  })

  it("clears the API's error when the field is edited, and opens the job once accepted", async () => {
    serveValidationProblem({ loc: ['body', 'csnp', 'input', 'species'], msg: 'Refused.' })
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)
    await user.click(submitButton())
    await waitFor(() => expect(speciesBox()).toBeInvalid())

    await user.clear(speciesBox())
    await user.type(speciesBox(), 'RAT')

    expect(speciesBox()).toBeValid()
    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })
})

describe('when the job is not started', () => {
  it('says cSNP scoring is not available yet on a 501, keeps the input, and stays', async () => {
    const bodies = serveProblem(501, csnpUnavailable)
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/isn.t available yet/i)
    expect(bodies).toHaveLength(1)
    expect(sequenceBox()).toHaveValue(SEQUENCE)
    expect(substitutionsBox()).toHaveValue('L4P c13r\nG12V')
    expect(speciesBox()).toHaveValue('HUMAN')
    expect(router.state.location.pathname).toBe('/csnp')
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
    const { user, router } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    const alert = await main().findByRole('alert')
    expect(alert).toHaveTextContent(/couldn.t be started/i)
    expect(alert).not.toHaveTextContent(/available yet/i)
    expect(screen.getByRole('main').textContent).not.toMatch(BUILD_DETAILS)
    expect(screen.getByRole('main').textContent).not.toMatch(/500|internal server error/i)
    expect(router.state.location.pathname).toBe('/csnp')
    expect(submitButton()).toBeEnabled()

    serveStart()
    await user.click(submitButton())
    await waitFor(() => expect(router.state.location.pathname).toMatch(JOB_PATH))
  })

  it('treats a 422 without field errors as a failure to start', async () => {
    serveProblem(422, { type: 'about:blank', title: 'x', status: 422, detail: 'x' })
    const { user } = renderRoute('/csnp')
    await fillValid(user)

    await user.click(submitButton())

    expect(await main().findByRole('alert')).toHaveTextContent(/couldn.t be started/i)
  })
})
