import { type Dispatch, useState } from 'react'
import { useNavigate } from 'react-router'

import { errorData, errorStatus } from '@/app/api/errors'
import { inputErrors, isValidationProblem } from '@/app/api/wire'
import { type SubmitProblem, submitProblem, warnSubmitProblem } from '@/components/submitProblem'
import { keepInput, useStartJobMutation } from '@/features/jobs'

import { type DraftAction, draftInput, REFMAP_FIELDS, type RefmapValues } from './draft'
import type { SplitIds } from './ids'

/**
 * Why the last submit didn't open a job, when it wasn't the input. This form's requirements give
 * every failure but a 422 and no answer at all one message, so a 501 or a busy 503 is `failed`.
 */
type ShownProblem = Extract<SubmitProblem, 'unreachable' | 'failed'> | null

/**
 * Starts a refmap job from the draft and its IDs as split. A 202 keeps the input as typed, for
 * "Edit and resubmit", and opens the job's page; a 422's errors go to the draft, on their
 * fields; any other failure is the returned `problem`.
 */
export function useSubmitRefmap(dispatch: Dispatch<DraftAction>) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [problem, setProblem] = useState<ShownProblem>(null)
  const navigate = useNavigate()

  async function submit(values: RefmapValues, split: SplitIds) {
    setProblem(null)
    const input = draftInput(values, split)
    try {
      const job = await startJob({ service: 'refmap', input }).unwrap()
      keepInput(job.id, 'refmap', values)
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const status = errorStatus(error)
      const data = errorData(error)
      if (status === 422 && isValidationProblem(data) && data.errors.length > 0) {
        dispatch({ type: 'rejected', ...inputErrors(data, 'refmap', REFMAP_FIELDS), sent: split })
        return
      }
      const problem = submitProblem(error)
      warnSubmitProblem('refmap', problem, error)
      setProblem(problem === 'unreachable' ? 'unreachable' : 'failed')
    }
  }

  return { submit, isSubmitting: isLoading, problem }
}
