import { api } from '@/app/api/api'
import type { components } from '@/app/api/schema'

export type Versions = components['schemas']['Versions']

export const versionsApi = api.injectEndpoints({
  endpoints: build => ({
    getVersions: build.query<Versions, void>({ query: () => 'versions' }),
  }),
})

export const { useGetVersionsQuery } = versionsApi
