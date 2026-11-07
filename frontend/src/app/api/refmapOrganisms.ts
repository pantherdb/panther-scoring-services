import { api } from '@/app/api/api'
import type { RefmapOrganism } from '@/app/api/wire'

// Here rather than in features/refmap: the form offers the organisms, and the job page names
// the one a job mapped against. One cached request serves both.
export const refmapOrganismsApi = api.injectEndpoints({
  endpoints: build => ({
    // The organisms refmap maps for, with their names and gene counts, in the API's order.
    getRefmapOrganisms: build.query<RefmapOrganism[], void>({ query: () => 'refmap/organisms' }),
  }),
})

export const { useGetRefmapOrganismsQuery } = refmapOrganismsApi
