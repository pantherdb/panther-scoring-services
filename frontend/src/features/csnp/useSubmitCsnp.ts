import { type Dispatch, useState } from 'react'
import { useNavigate } from 'react-router'

import { isUnreachable } from '@/app/api/errors'
import { inputErrors, isValidationProblem } from '@/app/api/wire'
import { useStartJobMutation } from '@/features/jobs'

import { CSNP_FIELDS, type CsnpValues, type DraftAction, draftInput } from './draft'

/**
 * Why the last submit didn't open a job, when it wasn't the input: `unreachable` is no
 * answer from the API at all; `failed` is anything else.
 */
export type SubmitProblem = 'unreachable' | 'failed' | null

function statusOf(error: unknown) {
  return typeof error === 'object' && error !== null && 'status' in error ? error.status : null
}

function dataOf(error: unknown) {
  return typeof error === 'object' && error !== null && 'data' in error ? error.data : null
}

/**
 * Starts a csnp job from the draft. A 202 opens the job's page; a 422's errors go to the
 * draft, on their fields; any other failure is the returned `problem`.
 */
export function useSubmitCsnp(dispatch: Dispatch<DraftAction>) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [problem, setProblem] = useState<SubmitProblem>(null)
  const navigate = useNavigate()

  async function submit(values: CsnpValues) {
    setProblem(null)
    const input = draftInput(values)
    try {
      const job = await startJob({ service: 'csnp', input }).unwrap()
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const status = statusOf(error)
      const data = dataOf(error)
      if (status === 422 && isValidationProblem(data) && data.errors.length > 0) {
        dispatch({
          type: 'rejected',
          ...inputErrors(data, 'csnp', CSNP_FIELDS),
          sent: input.substitutions,
        })
        return
      }
      if (isUnreachable(error)) {
        if (import.meta.env.DEV) {
          console.warn(
            'The API could not be reached. Is it running? See docs/testing/api.md',
            error
          )
        }
        setProblem('unreachable')
        return
      }
      // Shown with fixed text: the response could carry build details.
      if (import.meta.env.DEV) console.warn('The csnp job could not be started', error)
      setProblem('failed')
    }
  }

  return { submit, isSubmitting: isLoading, problem }
}
