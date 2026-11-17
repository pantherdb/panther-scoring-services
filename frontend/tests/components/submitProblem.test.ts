import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { makeStore } from '@/app/store'
import { retryAfterOf, submitFailure, submitProblem } from '@/components/submitProblem'
import { tryAgainIn } from '@/components/SubmitAlert'
import { jobsApi } from '@/features/jobs/jobsApi'

import { server } from '../mocks/server'

const PROBLEM = { 'Content-Type': 'application/problem+json' }

function problem(status: number) {
  return { type: 'about:blank', title: 'x', status, detail: 'at /opt/app :8000' }
}

describe('submitProblem', () => {
  it.each([
    ["the API's 501", { status: 501, data: problem(501) }, 'unavailable'],
    ["the API's busy 503", { status: 503, data: problem(503) }, 'busy'],
    ['a 501 with no problem details', { status: 501, data: null }, 'unreachable'],
    [
      'a 501 in HTML',
      { status: 'PARSING_ERROR', originalStatus: 501, data: '<html>' },
      'unreachable',
    ],
    ['a 503 with no problem details', { status: 503, data: 'Service Unavailable' }, 'unreachable'],
    ['a network failure', { status: 'FETCH_ERROR', error: 'TypeError' }, 'unreachable'],
    ["the API's 500", { status: 500, data: problem(500) }, 'failed'],
    ["the API's 413", { status: 413, data: problem(413) }, 'failed'],
    ['something not an error', 'Failed', 'failed'],
  ])('classifies %s', (_name, error, expected) => {
    expect(submitProblem(error)).toBe(expected)
  })
})

// Starts a job through the real endpoint, against a 503 with these headers, and returns the
// error unwrap() throws.
async function busyError(headers: Record<string, string>) {
  server.use(
    http.post('/api/v1/jobs', () =>
      HttpResponse.json(problem(503), { status: 503, headers: { ...PROBLEM, ...headers } })
    )
  )
  const store = makeStore()
  try {
    await store
      .dispatch(
        jobsApi.endpoints.startJob.initiate({ service: 'hmmscore', input: { sequence: 'MKV' } })
      )
      .unwrap()
  } catch (error) {
    return error
  }
  throw new Error('The job was started')
}

describe('submitFailure', () => {
  const validation = {
    ...problem(422),
    errors: [{ loc: ['body', 'hmmscore', 'input', 'sequence'], msg: 'Bad.', type: 'value_error' }],
  }

  it("is rejected, with the problem, for the API's 422 with errors", () => {
    expect(submitFailure('hmmscore', { status: 422, data: validation })).toEqual({
      problem: 'rejected',
      validation,
    })
  })

  it.each([
    ['a 422 with no errors', { status: 422, data: { ...validation, errors: [] } }],
    ['a 422 that is not a validation problem', { status: 422, data: problem(422) }],
  ])('is failed for %s, as the forms were before', (_name, error) => {
    expect(submitFailure('csnp', error)).toEqual({ problem: 'failed', retryAfter: null })
  })

  it("gives any other failure's problem, and its Retry-After", () => {
    const busy = { status: 503, data: problem(503), retryAfter: 30 }

    expect(submitFailure('hmmscore', busy)).toEqual({ problem: 'busy', retryAfter: 30 })
    expect(submitFailure('refmap', { status: 'FETCH_ERROR', error: 'x' })).toEqual({
      problem: 'unreachable',
      retryAfter: null,
    })
  })
})

describe("startJob's Retry-After", () => {
  it('adds whole seconds to the error, which stays busy', async () => {
    const error = await busyError({ 'Retry-After': '30' })

    expect(submitProblem(error)).toBe('busy')
    expect(retryAfterOf(error)).toBe(30)
  })

  it.each([
    ['missing', {}],
    ['an HTTP date', { 'Retry-After': 'Wed, 21 Oct 2026 07:28:00 GMT' }],
    ['not a number', { 'Retry-After': 'soon' }],
    ['a fraction', { 'Retry-After': '1.5' }],
  ])('gives no seconds when it is %s', async (_name, headers) => {
    const error = await busyError(headers)

    expect(submitProblem(error)).toBe('busy')
    expect(retryAfterOf(error)).toBeNull()
  })
})

describe('tryAgainIn', () => {
  it.each([
    [30, 'in about 30 seconds'],
    [90, 'in about 90 seconds'],
    [91, 'in about 2 minutes'],
    [300, 'in about 5 minutes'],
    [1, 'in a moment'],
    [null, 'in a few minutes'],
  ])('says %s seconds as %j', (seconds, text) => {
    expect(tryAgainIn(seconds)).toBe(text)
  })
})
