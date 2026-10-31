import { describe, expect, it } from 'vitest'

import { refmapResult } from '@/mocks/data/jobs'
import { createJob, pollJob } from '@/mocks/jobs'

const IDS = ['P04217', 'P01023', 'P02649', 'P04637', 'P38398', 'P00533', 'P04217']

describe('a mocked refmap job', () => {
  it('maps the IDs it was created with once it has succeeded, one per ID, in order', () => {
    const { id, result } = createJob('refmap', IDS)
    expect(result).toBeNull()

    pollJob(id)
    pollJob(id)
    const job = pollJob(id)

    expect(job?.status).toBe('succeeded')
    expect(job?.service === 'refmap' && job.result).toEqual(refmapResult(IDS))
  })

  it('maps the example to a mix of obviously made-up PANTHER IDs and none, the same each time', () => {
    const { mappings } = refmapResult(IDS)

    expect(mappings.map(mapping => mapping.id)).toEqual(IDS)
    const found = mappings.flatMap(({ panther_id }) => (panther_id === null ? [] : [panther_id]))
    expect(found.length).toBeGreaterThan(0)
    expect(found.length).toBeLessThan(IDS.length)
    for (const pantherId of found) expect(pantherId).toMatch(/^PTHR00000:SF\d$/)
    expect(mappings[6]).toEqual(mappings[0])
    expect(refmapResult(IDS)).toEqual(refmapResult(IDS))
  })
})
