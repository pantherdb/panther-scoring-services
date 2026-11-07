import { describe, expect, it } from 'vitest'

import { example } from '@/features/refmap/example'
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
    expect(job?.service === 'refmap' && job.result?.organism).toBe('ENDPU')
  })

  it('maps against the organism it was created with', () => {
    const { id } = createJob('refmap', IDS, 'ARAVE')

    pollJob(id)
    pollJob(id)
    const job = pollJob(id)

    expect(job?.service === 'refmap' && job.result).toEqual(refmapResult(IDS, 'ARAVE'))
    expect(job?.service === 'refmap' && job.result?.organism).toBe('ARAVE')
  })

  it("maps the form's example as the legacy service did, an unmapped ID included", () => {
    const ids = example.ids.split('\n')

    expect(refmapResult(ids).mappings).toEqual([
      { id: 'U1G4Q5', panther_id: 'PTHR11360:SF130' },
      { id: 'U1GCA1', panther_id: 'PTHR21058:SF0' },
      { id: 'U1HRR6', panther_id: 'PTHR42765:SF2' },
      { id: 'U1GLV9', panther_id: 'PTHR28011' },
      { id: 'U1GJ40', panther_id: 'PTHR13401' },
      { id: 'U1HQ27', panther_id: null },
    ])
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
