import { useState } from 'react'
import { useNavigate } from 'react-router'

import { HMMSCORE_FIELDS } from '@/app/formFields'
import { errorData, errorStatus } from '@/app/api/errors'
import { inputErrors, isValidationProblem } from '@/app/api/wire'
import {
  retryAfterOf,
  type SubmitProblem,
  submitProblem,
  warnSubmitProblem,
} from '@/components/submitProblem'
import { keepInput, useStartJobMutation } from '@/features/jobs'

import type { HmmscoreValues } from './checks'

/** Why the last submit didn't open a job, and the seconds to wait that a busy API gave. */
export type SubmitFailure = { problem: SubmitProblem; retryAfter: number | null }

/** A 422's messages: those on the sequence, and those on nothing the form has. */
export type Rejection = { sequence: string[]; other: string[] }

/**
 * Starts an hmmscore job from the box as typed; the API normalises it. A 202 keeps the input,
 * for "Edit and resubmit", and opens the job's page; a 422's messages go to `onRejected`; any
 * other failure is the returned `failure`.
 */
export function useSubmitHmmscore(onRejected: (rejection: Rejection) => void) {
  const [startJob, { isLoading }] = useStartJobMutation()
  const [failure, setFailure] = useState<SubmitFailure | null>(null)
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
      const data = errorData(error)
      if (errorStatus(error) === 422 && isValidationProblem(data) && data.errors.length > 0) {
        const { fields, other } = inputErrors(data, 'hmmscore', HMMSCORE_FIELDS)
        onRejected({ sequence: (fields.sequence ?? []).map(({ msg }) => msg), other })
        return
      }
      const problem = submitProblem(error)
      warnSubmitProblem('hmmscore', problem, error)
      setFailure({ problem, retryAfter: retryAfterOf(error) })
    }
  }

  return { submit, isSubmitting: isLoading, failure }
}
