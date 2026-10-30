import { isFinished, JOB_POLL_INTERVAL_MS, jobsApi, useGetJobQuery } from './jobsApi'

/**
 * The job with this id, checked every JOB_POLL_INTERVAL_MS while it's queued or
 * running. Checking stops once it has finished, or a request for it has failed.
 */
export function useJob(id: string) {
  // Read the cached entry without subscribing, so the interval is derived while
  // rendering, with no state to keep in step with the job.
  const cached = jobsApi.endpoints.getJob.useQueryState(id)
  const stop = cached.isError || (cached.data !== undefined && isFinished(cached.data.status))

  return useGetJobQuery(id, { pollingInterval: stop ? 0 : JOB_POLL_INTERVAL_MS })
}

/** Whether a failed request was a 404: an unknown, malformed or expired job id. */
export function isNotFound(error: unknown) {
  return typeof error === 'object' && error !== null && 'status' in error && error.status === 404
}
