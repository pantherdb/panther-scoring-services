import { afterEach, describe, expect, it, vi } from 'vitest'

import { keepInput, keptInput, MOST_KEPT } from '@/features/jobs/keptInput'

const VALUES = { sequence: 'MKVLW', substitutions: 'L4P, G2A', species: 'HUMAN' }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('the kept input', () => {
  it('reads back what was kept, for the same job and service', () => {
    keepInput('job-1', 'csnp', VALUES)

    expect(keptInput('job-1', 'csnp')).toEqual(VALUES)
  })

  it('has nothing for a job never kept', () => {
    keepInput('job-1', 'csnp', VALUES)

    expect(keptInput('job-2', 'csnp')).toBeUndefined()
  })

  it("has nothing for another service's form", () => {
    keepInput('job-1', 'csnp', VALUES)

    expect(keptInput('job-1', 'refmap')).toBeUndefined()
  })

  it.each([
    ['not JSON', '{'],
    ['not an object', '"text"'],
    ['no values', '{"service":"csnp"}'],
    ['a value that is not text', '{"service":"csnp","values":{"sequence":5}}'],
  ])('reads an entry that is %s as nothing', (_what, raw) => {
    window.sessionStorage.setItem('panther-scoring:input:job-1', raw)

    expect(keptInput('job-1', 'csnp')).toBeUndefined()
  })

  it(`keeps the last ${MOST_KEPT} jobs, dropping the oldest`, () => {
    for (let i = 0; i <= MOST_KEPT; i++) keepInput(`job-${i}`, 'csnp', VALUES)

    expect(keptInput('job-0', 'csnp')).toBeUndefined()
    expect(keptInput('job-1', 'csnp')).toEqual(VALUES)
    expect(keptInput(`job-${MOST_KEPT}`, 'csnp')).toEqual(VALUES)
  })

  it('keeps nothing, without throwing, when the storage is full', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('full', 'QuotaExceededError')
    })

    expect(() => keepInput('job-1', 'refmap', { ids: 'P1', organism: 'HUMAN' })).not.toThrow()
    vi.restoreAllMocks()
    expect(keptInput('job-1', 'refmap')).toBeUndefined()
  })

  it('reads nothing, without throwing, when the storage throws', () => {
    keepInput('job-1', 'csnp', VALUES)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError')
    })

    expect(keptInput('job-1', 'csnp')).toBeUndefined()
  })
})
