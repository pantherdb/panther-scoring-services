import { type Dispatch, useState } from 'react'
import { useNavigate } from 'react-router'

import { errorData, errorStatus, isUnreachable } from '@/app/api/errors'
import { inputErrors, isValidationProblem } from '@/app/api/wire'
import { useStartJobMutation } from '@/features/jobs'

import { type DraftAction, draftInput, REFMAP_FIELDS, type RefmapValues } from './draft'
import type { SplitIds } from './ids'

/**
 * Why the last submit didn't open a job, when it wasn't the input: `unavailable` is the
 * API's 501 until refmap mapping is ported; `unreachable` is no answer from the API at all;
 * `failed` is anything else.
 */
export type SubmitProblem = 'unavailable' | 'unreachable' | 'failed' | null

/**
 * Starts a refmap job from the draft and its IDs as split. A 202 opens the job's page; a
 * 422's errors go to the draft, on their fields; a 501 or any other failure is the returned
 * `problem`.
 */
export function useSubmitRefmap(dispatch: Dispatch<DraftAction>) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [problem, setProblem] = useState<SubmitProblem>(null)
  const navigate = useNavigate()

  async function submit(values: RefmapValues, split: SplitIds) {
    setProblem(null)
    const input = draftInput(values, split)
    try {
      const job = await startJob({ service: 'refmap', input }).unwrap()
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const status = errorStatus(error)
      const data = errorData(error)
      if (status === 422 && isValidationProblem(data) && data.errors.length > 0) {
        dispatch({ type: 'rejected', ...inputErrors(data, 'refmap', REFMAP_FIELDS), sent: split })
        return
      }
      if (status === 501) {
        setProblem('unavailable')
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
      if (import.meta.env.DEV) console.warn('The refmap job could not be started', error)
      setProblem('failed')
    }
  }

  return { submit, isSubmitting: isLoading, problem }
}
