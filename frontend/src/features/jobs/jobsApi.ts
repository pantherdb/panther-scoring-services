import { api } from '@/app/api/api'
import {
  fromWireJob,
  type Job,
  type JobRequest,
  type JobStatus,
  type WireJob,
} from '@/app/api/wire'

/**
 * How often a queued or running job is checked. The tools job finishes in about
 * 1.5 s, so each status shows as it happens; a poll is a small in-memory lookup.
 */
export const JOB_POLL_INTERVAL_MS = 1000

export function isFinished(status: JobStatus) {
  return status === 'succeeded' || status === 'failed'
}

export const jobsApi = api.injectEndpoints({
  endpoints: build => ({
    startJob: build.mutation<Job, JobRequest>({
      query: body => ({ url: 'jobs', method: 'POST', body }),
      transformResponse: (wire: WireJob) => fromWireJob(wire),
    }),
    getJob: build.query<Job, string>({
      query: id => `jobs/${encodeURIComponent(id)}`,
      transformResponse: (wire: WireJob) => fromWireJob(wire),
    }),
  }),
})

export const { useStartJobMutation, useGetJobQuery } = jobsApi
