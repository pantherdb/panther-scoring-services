import { type Dispatch, useState } from 'react'
import { useNavigate } from 'react-router'

import { inputErrors } from '@/app/api/wire'
import { type NotStarted, submitFailure } from '@/components/submitProblem'
import { keepInput, useStartJobMutation } from '@/features/jobs'

import { type DraftAction, draftInput, REFMAP_FIELDS, type RefmapValues } from './draft'
import type { SplitIds } from './ids'

/**
 * Starts a refmap job from the draft and its IDs as split. A 202 keeps the input as typed, for
 * "Edit and resubmit", and opens the job's page; a 422's errors go to the draft, on their
 * fields; any other failure, a 501 from an older API included, is the returned `failure`, which
 * the form shows with `SubmitAlert`'s `limited` set.
 */
export function useSubmitRefmap(dispatch: Dispatch<DraftAction>) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [failure, setFailure] = useState<NotStarted | null>(null)
  const navigate = useNavigate()

  async function submit(values: RefmapValues, split: SplitIds) {
    setFailure(null)
    const input = draftInput(values, split)
    try {
      const job = await startJob({ service: 'refmap', input }).unwrap()
      keepInput(job.id, 'refmap', values)
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const failure = submitFailure('refmap', error)
      if (failure.problem === 'rejected') {
        const errors = inputErrors(failure.validation, 'refmap', REFMAP_FIELDS)
        dispatch({ type: 'rejected', ...errors, sent: split })
        return
      }
      setFailure(failure)
    }
  }

  return { submit, isSubmitting: isLoading, failure }
}
