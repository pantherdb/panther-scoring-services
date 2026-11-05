import { skipToken } from '@reduxjs/toolkit/query'
import { useMatch } from 'react-router'

import type { JobService } from '@/app/api/wire'

import { jobsApi } from './jobsApi'

/**
 * On a job's page, the service of the job shown, once it has loaded; anywhere else, none.
 * Read from the cache the job's page fills, so it sends no request of its own.
 */
export function useShownJobService(): JobService | undefined {
  const id = useMatch('/jobs/:id')?.params.id
  const { data } = jobsApi.endpoints.getJob.useQueryState(id ?? skipToken)
  return id === undefined ? undefined : data?.service
}
