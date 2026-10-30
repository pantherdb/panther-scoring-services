import { describe, expect, it } from 'vitest'

import { byName } from '@/features/csnp/useCsnpSpecies'

describe('byName', () => {
  it('sorts the species by name, and leaves the list it was given as it was', () => {
    const species = [
      { code: 'HUMAN', name: 'Homo sapiens' },
      { code: 'ARATH', name: 'Arabidopsis thaliana' },
      { code: 'MOUSE', name: 'Mus musculus' },
    ]

    expect(byName(species).map(({ code }) => code)).toEqual(['ARATH', 'HUMAN', 'MOUSE'])
    expect(species.map(({ code }) => code)).toEqual(['HUMAN', 'ARATH', 'MOUSE'])
  })
})
