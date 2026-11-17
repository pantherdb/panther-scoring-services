import { api } from '@/app/api/api'
import {
  fromWireJob,
  type Job,
  type JobRequest,
  type JobStatus,
  type WireJob,
} from '@/app/api/wire'

/**
 * How often a queued or running job is checked at first. The tools job finishes in about
 * 1.5 s, so each status shows as it happens; a poll is a small in-memory lookup.
 */
export const JOB_POLL_INTERVAL_MS = 1000
/** How long a job is checked every JOB_POLL_INTERVAL_MS after its page opens. */
export const JOB_FAST_POLL_FOR_MS = 30_000
/**
 * How often a job is checked after that: an hmmscore job can wait behind the running cap, then
 * run for up to 720 s, and checking every second would send hundreds of requests.
 */
export const JOB_SLOW_POLL_INTERVAL_MS = 5000

/** How often to check a job, by whether its page has been open past JOB_FAST_POLL_FOR_MS. */
export function jobPollInterval(slow: boolean) {
  return slow ? JOB_SLOW_POLL_INTERVAL_MS : JOB_POLL_INTERVAL_MS
}

/**
 * The seconds a `Retry-After` header gives, when it's a whole number of them; otherwise, as for
 * an HTTP date or no header, null.
 */
export function retryAfterSeconds(header: string | null): number | null {
  const value = header?.trim() ?? ''
  return /^\d+$/.test(value) ? Number(value) : null
}

export function isFinished(status: JobStatus) {
  return status === 'succeeded' || status === 'failed'
}

export const jobsApi = api.injectEndpoints({
  endpoints: build => ({
    startJob: build.mutation<Job, JobRequest>({
      query: body => ({ url: 'jobs', method: 'POST', body }),
      transformResponse: (wire: WireJob) => fromWireJob(wire),
      // unwrap() drops the response, so a busy 503's Retry-After is added to the error here.
      transformErrorResponse: (error, meta) => ({
        ...error,
        retryAfter: retryAfterSeconds(meta?.response?.headers.get('Retry-After') ?? null),
      }),
    }),
    getJob: build.query<Job, string>({
      query: id => `jobs/${encodeURIComponent(id)}`,
      transformResponse: (wire: WireJob) => fromWireJob(wire),
    }),
  }),
})

export const { useStartJobMutation, useGetJobQuery } = jobsApi
