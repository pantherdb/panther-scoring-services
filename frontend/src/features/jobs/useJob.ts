import { useEffect, useState } from 'react'

import type { Job } from '@/app/api/wire'

import {
  isFinished,
  JOB_FAST_POLL_FOR_MS,
  jobPollInterval,
  jobsApi,
  useGetJobQuery,
} from './jobsApi'

/**
 * When an hmmscore job, which can wait behind the running cap and then run for up to 720 s, was
 * created; null for any other job, or none yet. Other services' jobs finish in seconds, or about
 * 30 s for a typical cSNP job, so they're checked every second throughout.
 */
function slowsAfter(job: Job | undefined): number | null {
  return job?.service === 'hmmscore' ? job.createdAt : null
}

/**
 * Whether the job with this id is an hmmscore job created more than JOB_FAST_POLL_FOR_MS ago. A
 * timer set for the rest of that time marks the id, so no clock is read while rendering; a
 * reload, or another person opening the link, doesn't start the fast checks again. Going back to
 * an earlier job sets its own timer, which fires at once if its time is up. The job's
 * `createdAt` is the API's clock; a browser clock that differs only moves when it slows.
 */
function useSlowPolling(id: string, createdAt: number | null) {
  const [slowFor, setSlowFor] = useState<string | null>(null)
  useEffect(() => {
    if (createdAt === null) return
    const wait = Math.max(0, createdAt + JOB_FAST_POLL_FOR_MS - Date.now())
    const timer = setTimeout(() => setSlowFor(id), wait)
    return () => clearTimeout(timer)
  }, [id, createdAt])
  return createdAt !== null && slowFor === id
}

/**
 * The job with this id, checked while it's queued or running: every second, and for an hmmscore
 * job every 5 seconds once 30 seconds have passed since it was created (jobPollInterval).
 * Checking stops once it has finished, or a request for it has failed.
 */
export function useJob(id: string) {
  // Read the cached entry without subscribing, so the interval is derived while
  // rendering, with no state to keep in step with the job.
  const cached = jobsApi.endpoints.getJob.useQueryState(id)
  const slow = useSlowPolling(id, slowsAfter(cached.data))
  const stop = cached.isError || (cached.data !== undefined && isFinished(cached.data.status))

  return useGetJobQuery(id, { pollingInterval: stop ? 0 : jobPollInterval(slow) })
}

/** Whether a failed request was a 404: an unknown, malformed or expired job id. */
export function isNotFound(error: unknown) {
  return typeof error === 'object' && error !== null && 'status' in error && error.status === 404
}
