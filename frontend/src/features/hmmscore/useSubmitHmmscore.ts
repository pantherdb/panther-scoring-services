import { useState } from 'react'
import { useNavigate } from 'react-router'

import { HMMSCORE_FIELDS } from '@/app/formFields'
import { inputErrors } from '@/app/api/wire'
import { type NotStarted, submitFailure } from '@/components/submitProblem'
import { keepInput, useStartJobMutation } from '@/features/jobs'

import type { HmmscoreValues } from './checks'

/** A 422's messages: those on the sequence, and those on nothing the form has. */
export type Rejection = { sequence: string[]; other: string[] }

/**
 * Starts an hmmscore job from the box as typed; the API normalises it. A 202 keeps the input,
 * for "Edit and resubmit", and opens the job's page; a 422's messages go to `onRejected`; any
 * other failure is the returned `failure`.
 */
export function useSubmitHmmscore(onRejected: (rejection: Rejection) => void) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [failure, setFailure] = useState<NotStarted | null>(null)
  const navigate = useNavigate()

  async function submit(values: HmmscoreValues) {
    setFailure(null)
    try {
      const job = await startJob({
        service: 'hmmscore',
        input: { sequence: values.sequence },
      }).unwrap()
      keepInput(job.id, 'hmmscore', values)
      await navigate(`/jobs/${job.id}`)
    } catch (error) {
      const failure = submitFailure('hmmscore', error)
      if (failure.problem === 'rejected') {
        const { fields, other } = inputErrors(failure.validation, 'hmmscore', HMMSCORE_FIELDS)
        onRejected({ sequence: (fields.sequence ?? []).map(({ msg }) => msg), other })
        return
      }
      setFailure(failure)
    }
  }

  /** Hides the last failure, once what it was about has changed or another check has failed. */
  function clearFailure() {
    setFailure(null)
  }

  return { submit, isSubmitting: isLoading, failure, clearFailure }
}
