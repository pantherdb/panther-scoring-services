import { describe, expect, it } from 'vitest'

import { example } from '@/features/refmap/example'
import { hmmscoreResult, MOCK_ALIGNMENT_WIDTH, refmapResult } from '@/mocks/data/jobs'
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

describe('a mocked hmmscore job', () => {
  it('succeeds with the mock hit, after queued and running', () => {
    const { id, service, result } = createJob('hmmscore')
    expect(service).toBe('hmmscore')
    expect(result).toBeNull()

    expect(pollJob(id)?.status).toBe('queued')
    expect(pollJob(id)?.status).toBe('running')
    const job = pollJob(id)

    expect(job?.status).toBe('succeeded')
    expect(job?.service === 'hmmscore' && job.result).toEqual(hmmscoreResult)
  })

  it('says it was created when it was made, so its page checks it every second at first', () => {
    const before = Date.now()
    const { id, created_at } = createJob('hmmscore')

    expect(Date.parse(created_at)).toBeGreaterThanOrEqual(before)
    expect(Date.parse(created_at)).toBeLessThanOrEqual(Date.now())
    expect(pollJob(id)?.created_at).toBe(created_at)
  })

  it('has an obviously made-up hit, and an alignment marked as mock, wider than a phone', () => {
    const { hit } = hmmscoreResult

    expect(hit?.panther_id).toBe('PTHR00000:SF1')
    expect(hit?.name).toMatch(/mock/i)
    const lines = hit?.alignment.split('\n') ?? []
    expect(lines[0]).toMatch(/mock data/i)
    expect(lines.length).toBeGreaterThan(2)
    for (const line of lines) expect(line).toHaveLength(MOCK_ALIGNMENT_WIDTH)
    expect(MOCK_ALIGNMENT_WIDTH).toBe(200)
  })
})
