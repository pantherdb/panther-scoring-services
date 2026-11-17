import { errorData, errorStatus, isUnreachable } from '@/app/api/errors'

/**
 * Why a submit didn't open a job, when it wasn't the input (a 422, which each form shows on its
 * own fields): `unavailable` is the API's 501, a service it can't run yet; `busy` its 503, too
 * many jobs waiting; `unreachable` no answer from the API at all; `failed` anything else.
 */
export type SubmitProblem = 'unavailable' | 'busy' | 'unreachable' | 'failed'

function hasProblemDetails(error: unknown) {
  const data = errorData(error)
  return typeof data === 'object' && data !== null && 'status' in data && 'title' in data
}

/**
 * Classifies a failed `startJob`. A 501 or 503 without problem details came from something in
 * between, such as nginx answering 501 for a `Transfer-Encoding` it doesn't support, so it's
 * `unreachable`, as `isUnreachable` says.
 */
export function submitProblem(error: unknown): SubmitProblem {
  if (isUnreachable(error)) return 'unreachable'
  const status = errorStatus(error)
  if (status === 501 && hasProblemDetails(error)) return 'unavailable'
  if (status === 503 && hasProblemDetails(error)) return 'busy'
  return 'failed'
}

/**
 * The seconds a failed `startJob` was told to wait, from the `Retry-After` header that
 * `startJob` adds to its error (`retryAfter`); null without one.
 */
export function retryAfterOf(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('retryAfter' in error)) return null
  const { retryAfter } = error
  return typeof retryAfter === 'number' ? retryAfter : null
}

/**
 * Logs why a job wasn't started, in development only: the screen shows fixed text, since the
 * response could carry build details.
 */
export function warnSubmitProblem(service: string, problem: SubmitProblem, error: unknown) {
  if (!import.meta.env.DEV) return
  if (problem === 'unreachable') {
    console.warn('The API could not be reached. Is it running? See docs/testing/api.md', error)
  } else {
    console.warn(`The ${service} job could not be started`, error)
  }
}
