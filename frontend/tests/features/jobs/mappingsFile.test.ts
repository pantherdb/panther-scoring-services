import { describe, expect, it } from 'vitest'

import { mappingsFileName, mappingsTsv } from '@/features/jobs/mappingsFile'

describe('mappingsTsv', () => {
  it('writes a header, then one line per mapping in order, empty for no PANTHER ID', () => {
    expect(
      mappingsTsv([
        { id: 'P04217', panther_id: 'PTHR00000:SF4' },
        { id: 'p04217', panther_id: null },
        { id: 'P04217', panther_id: 'PTHR00000:SF4' },
      ])
    ).toBe('id\tpanther_id\nP04217\tPTHR00000:SF4\np04217\t\nP04217\tPTHR00000:SF4\n')
  })

  it('writes only the header for no mappings', () => {
    expect(mappingsTsv([])).toBe('id\tpanther_id\n')
  })

  it('writes 100,000 mappings quickly', () => {
    const mappings = Array.from({ length: 100_000 }, (_, i) => ({
      id: `P${i}`,
      panther_id: i % 3 === 0 ? null : 'PTHR00000:SF1',
    }))

    const start = performance.now()
    const lines = mappingsTsv(mappings).split('\n')

    expect(performance.now() - start).toBeLessThan(500)
    expect(lines).toHaveLength(100_002)
    expect(lines.slice(99_999)).toEqual(['P99998\tPTHR00000:SF1', 'P99999\t', ''])
  })
})

describe('mappingsFileName', () => {
  it("names the file after the job's id", () => {
    expect(mappingsFileName('0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001')).toBe(
      'panther-id-mapping-0b6f5ad2-5d1e-4f63-9f4e-3c1de2a8f001.tsv'
    )
  })
})
