import { type Dispatch, useState } from 'react'
import { useNavigate } from 'react-router'

import { inputErrors } from '@/app/api/wire'
import { type NotStarted, submitFailure } from '@/components/submitProblem'
import { keepInput, useStartJobMutation } from '@/features/jobs'

import { CSNP_FIELDS, type CsnpValues, type DraftAction, draftInput } from './draft'

/**
 * Starts a csnp job from the draft. A 202 keeps the input as typed, for "Edit and
 * resubmit", and opens the job's page; a 422's errors go to the
 * draft, on their fields; any other failure is the returned `failure`, which the form shows
 * with `SubmitAlert`'s `limited` set.
 */
export function useSubmitCsnp(dispatch: Dispatch<DraftAction>) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [failure, setFailure] = useState<NotStarted | null>(null)
  const navigate = useNavigate()

  async function submit(values: CsnpValues) {
    setFailure(null)
    const input = draftInput(values)
    try {
      const job = await startJob({ service: 'csnp', input }).unwrap()
      keepInput(job.id, 'csnp', values)
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const failure = submitFailure('csnp', error)
      if (failure.problem === 'rejected') {
        dispatch({
          type: 'rejected',
          ...inputErrors(failure.validation, 'csnp', CSNP_FIELDS),
          sent: input.substitutions,
        })
        return
      }
      setFailure(failure)
    }
  }

  return { submit, isSubmitting: isLoading, failure }
}
