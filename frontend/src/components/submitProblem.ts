import { errorData, errorStatus, isProblem, isUnreachable } from '@/app/api/errors'
import { isValidationProblem, type ValidationProblem } from '@/app/api/wire'

/**
 * Why a submit didn't open a job, when it wasn't the input: `unavailable` is the API's 501, a
 * service it can't run yet; `busy` its 503, too many jobs waiting; `unreachable` no answer from
 * the API at all; `failed` anything else.
 */
export type SubmitProblem = 'unavailable' | 'busy' | 'unreachable' | 'failed'

/** Why a submit didn't open a job, with what the form needs to say so. */
export type SubmitFailure =
  /** The API's 422, whose errors each form puts on its own fields. */
  | { problem: 'rejected'; validation: ValidationProblem }
  /** Any other failure, with the seconds to wait that a busy API gave, if any. */
  | NotStarted

/** A failure that isn't about the input: the form shows it with `SubmitAlert`. */
export type NotStarted = { problem: SubmitProblem; retryAfter: number | null }

/**
 * Classifies a failed `startJob`, other than its 422. A 501 or 503 without problem details came
 * from something in between, such as nginx answering 501 for a `Transfer-Encoding` it doesn't
 * support, so it's `unreachable`, as `isUnreachable` says.
 */
export function submitProblem(error: unknown): SubmitProblem {
  if (isUnreachable(error)) return 'unreachable'
  const status = errorStatus(error)
  if (status === 501 && isProblem(errorData(error))) return 'unavailable'
  if (status === 503 && isProblem(errorData(error))) return 'busy'
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
 * Why a `startJob` for `service` failed: `rejected`, with its problem, for a 422 that names at
 * least one error; otherwise its `submitProblem` and `Retry-After`, logged in development only,
 * since the screen shows fixed text and the response could carry build details. Every form's
 * submit hook reads its failure here, so the three classify alike.
 */
export function submitFailure(service: string, error: unknown): SubmitFailure {
  const data = errorData(error)
  if (errorStatus(error) === 422 && isValidationProblem(data) && data.errors.length > 0) {
    return { problem: 'rejected', validation: data }
  }
  const problem = submitProblem(error)
  if (import.meta.env.DEV) {
    if (problem === 'unreachable') {
      console.warn('The API could not be reached. Is it running? See docs/testing/api.md', error)
    } else {
      console.warn(`The ${service} job could not be started`, error)
    }
  }
  return { problem, retryAfter: retryAfterOf(error) }
}
