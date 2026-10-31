import { describe, expect, it } from 'vitest'

import {
  fromWireJob,
  inputErrors,
  isValidationProblem,
  type ValidationProblem,
  type WireJob,
} from '@/app/api/wire'

const versions = {
  api: '0.1.0',
  engine: '0.1.0',
  tools: [
    { name: 'blastp', version: '2.17.0' },
    { name: 'epa-ng', version: null },
  ],
  data: [{ service: 'csnp', panther: '9' }],
}

const succeeded: WireJob = {
  id: 'c56f34dc-cf36-429d-83d9-dcac03e46957',
  service: 'tools',
  status: 'succeeded',
  created_at: '2026-10-30T00:32:00.020522Z',
  started_at: '2026-10-30T00:32:00.021159Z',
  finished_at: '2026-10-30T00:32:01.540021Z',
  result: { tools: versions.tools },
  error: null,
  versions,
}

describe('fromWireJob', () => {
  it("renames the API's fields and turns its timestamps into epoch milliseconds", () => {
    expect(fromWireJob(succeeded)).toEqual({
      id: 'c56f34dc-cf36-429d-83d9-dcac03e46957',
      service: 'tools',
      status: 'succeeded',
      createdAt: Date.UTC(2026, 9, 30, 0, 32, 0, 20),
      startedAt: Date.UTC(2026, 9, 30, 0, 32, 0, 21),
      finishedAt: Date.UTC(2026, 9, 30, 0, 32, 1, 540),
      result: { tools: versions.tools },
      error: null,
      versions,
    })
  })

  it('keeps timestamps that are not reached yet as null', () => {
    const queued = fromWireJob({
      ...succeeded,
      status: 'queued',
      started_at: null,
      finished_at: null,
      result: null,
    })

    expect(queued.startedAt).toBeNull()
    expect(queued.finishedAt).toBeNull()
    expect(queued.createdAt).toBe(Date.UTC(2026, 9, 30, 0, 32, 0, 20))
  })

  it("passes a failed job's error through unchanged", () => {
    const error = {
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'The job failed.',
    }

    const failed = fromWireJob({ ...succeeded, status: 'failed', result: null, error })

    expect(failed.error).toEqual(error)
    expect(failed.result).toBeNull()
  })

  it('leaves no snake_case field in the result', () => {
    const keys = Object.keys(fromWireJob(succeeded))

    expect(keys.filter(key => key.includes('_'))).toEqual([])
  })
})

const csnpResult = {
  family: 'PTHR00000',
  scores: [
    { substitution: 'L46P', age: 100, message: 'a message', pdel: '0.50' },
    { substitution: 'R176C', age: null, message: 'Not scored: Invalid substitution', pdel: null },
  ],
}

describe('fromWireJob, for a csnp job', () => {
  it('keeps its service and result, null age and pdel included, unchanged', () => {
    const wire: WireJob = { ...succeeded, service: 'csnp', result: csnpResult }

    const job = fromWireJob(wire)

    expect(job.service).toBe('csnp')
    expect(job.result).toEqual(csnpResult)
    expect(job.finishedAt).toBe(Date.UTC(2026, 9, 30, 0, 32, 1, 540))
  })
})

describe('fromWireJob, for a refmap job', () => {
  it('keeps its service and mappings, null PANTHER IDs and repeats included, unchanged', () => {
    const refmapResult = {
      mappings: [
        { id: 'P04217', panther_id: 'PTHR00000:SF1' },
        { id: 'P38398', panther_id: null },
        { id: 'P04217', panther_id: 'PTHR00000:SF1' },
      ],
    }
    const wire: WireJob = { ...succeeded, service: 'refmap', result: refmapResult }

    const job = fromWireJob(wire)

    expect(job.service).toBe('refmap')
    expect(job.result).toEqual(refmapResult)
    expect(job.finishedAt).toBe(Date.UTC(2026, 9, 30, 0, 32, 1, 540))
  })
})

describe('inputErrors, for a refmap 422', () => {
  it('puts each error on the refmap field its loc names, with the ID it is about', () => {
    const refused: ValidationProblem = {
      type: 'about:blank',
      title: 'Unprocessable Content',
      status: 422,
      detail: 'Request validation failed',
      errors: [
        { loc: ['body', 'refmap', 'input', 'ids', 3], msg: 'Bad ID.', type: 'value_error' },
        { loc: ['body', 'refmap', 'input', 'organism'], msg: 'Bad.', type: 'value_error' },
        { loc: ['body', 'csnp', 'input', 'ids'], msg: 'Other service.', type: 'value_error' },
      ],
    }

    expect(inputErrors(refused, 'refmap', ['ids', 'organism'])).toEqual({
      fields: { ids: [{ msg: 'Bad ID.', item: 3 }], organism: [{ msg: 'Bad.', item: null }] },
      other: ['Other service.'],
    })
  })
})

const problem: ValidationProblem = {
  type: 'about:blank',
  title: 'Unprocessable Content',
  status: 422,
  detail: 'Request validation failed',
  errors: [
    { loc: ['body', 'csnp', 'input', 'species'], msg: 'Bad species.', type: 'value_error' },
    { loc: ['body', 'csnp', 'input', 'substitutions', 2], msg: 'Bad token.', type: 'value_error' },
    { loc: ['body', 'csnp', 'input', 'species'], msg: 'Still bad.', type: 'value_error' },
    { loc: ['body', 'csnp', 'input', 'organism'], msg: 'Extra input.', type: 'extra_forbidden' },
    { loc: ['body'], msg: 'Body broken.', type: 'json_invalid' },
  ],
}

const CSNP_FIELDS = ['sequence', 'substitutions', 'species'] as const

describe('isValidationProblem', () => {
  it('accepts a 422 validation problem', () => {
    expect(isValidationProblem(problem)).toBe(true)
  })

  it.each([
    ['a plain problem', { type: 'about:blank', title: 'x', status: 501, detail: 'x' }],
    ['errors that are not a list', { ...problem, errors: 'no' }],
    ['an error without a loc', { ...problem, errors: [{ msg: 'x', type: 'x' }] }],
    ['null', null],
    ['text', 'Unprocessable Content'],
  ])('refuses %s', (_name, value) => {
    expect(isValidationProblem(value)).toBe(false)
  })
})

describe('inputErrors', () => {
  it("puts each error's msg on the input field its loc names, in order, with a list item's index", () => {
    const { fields } = inputErrors(problem, 'csnp', CSNP_FIELDS)

    expect(fields).toEqual({
      species: [
        { msg: 'Bad species.', item: null },
        { msg: 'Still bad.', item: null },
      ],
      substitutions: [{ msg: 'Bad token.', item: 2 }],
    })
  })

  it('keeps an error on a field the form does not have, or on no field, under other', () => {
    const { other } = inputErrors(problem, 'csnp', CSNP_FIELDS)

    expect(other).toEqual(['Extra input.', 'Body broken.'])
  })

  it("does not put another service's errors on this service's fields", () => {
    const { fields, other } = inputErrors(problem, 'tools', CSNP_FIELDS)

    expect(fields).toEqual({})
    expect(other).toHaveLength(problem.errors.length)
  })
})
