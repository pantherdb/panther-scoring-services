import type { components } from '@/app/api/schema'

// The mocked GET /api/v1/csnp/species body: eight of the 85 species cSNP scores against, with
// their real codes and names, in code order as the API gives them. Also read by the @mock e2e
// spec, so keep this file free of runtime imports.
export const species: components['schemas']['CsnpSpecies'][] = [
  { code: 'ARATH', name: 'Arabidopsis thaliana' },
  { code: 'CAEEL', name: 'Caenorhabditis elegans' },
  { code: 'DANRE', name: 'Danio rerio' },
  { code: 'DROME', name: 'Drosophila melanogaster' },
  { code: 'HUMAN', name: 'Homo sapiens' },
  { code: 'MOUSE', name: 'Mus musculus' },
  { code: 'PLAF7', name: 'Plasmodium falciparum' },
  { code: 'RAT', name: 'Rattus norvegicus' },
]
