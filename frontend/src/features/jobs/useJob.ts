import { useEffect, useState } from 'react'

import {
  isFinished,
  JOB_FAST_POLL_FOR_MS,
  jobPollInterval,
  jobsApi,
  useGetJobQuery,
} from './jobsApi'

/**
 * Whether the page has shown the job with this id for longer than JOB_FAST_POLL_FOR_MS. A timer
 * sets it, so no clock is read while rendering; another id starts again.
 */
function useSlowPolling(id: string) {
  const [slowFor, setSlowFor] = useState<string | null>(null)
  useEffect(() => {
    const timer = setTimeout(() => setSlowFor(id), JOB_FAST_POLL_FOR_MS)
    return () => clearTimeout(timer)
  }, [id])
  return slowFor === id
}

/**
 * The job with this id, checked every second for its first 30 seconds on the page, then every
 * 5 seconds, while it's queued or running (jobPollInterval). Checking stops once it has
 * finished, or a request for it has failed.
 */
export function useJob(id: string) {
  const slow = useSlowPolling(id)
  // Read the cached entry without subscribing, so the interval is derived while
  // rendering, with no state to keep in step with the job.
  const cached = jobsApi.endpoints.getJob.useQueryState(id)
  const stop = cached.isError || (cached.data !== undefined && isFinished(cached.data.status))

  return useGetJobQuery(id, { pollingInterval: stop ? 0 : jobPollInterval(slow) })
}

/** Whether a failed request was a 404: an unknown, malformed or expired job id. */
export function isNotFound(error: unknown) {
  return typeof error === 'object' && error !== null && 'status' in error && error.status === 404
}
