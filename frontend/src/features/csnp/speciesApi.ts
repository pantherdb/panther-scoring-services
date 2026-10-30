import { api } from '@/app/api/api'
import type { CsnpSpecies } from '@/app/api/wire'

export const speciesApi = api.injectEndpoints({
  endpoints: build => ({
    // The species cSNP scores against, with their names, in the API's order.
    getCsnpSpecies: build.query<CsnpSpecies[], void>({ query: () => 'csnp/species' }),
  }),
})

export const { useGetCsnpSpeciesQuery } = speciesApi
