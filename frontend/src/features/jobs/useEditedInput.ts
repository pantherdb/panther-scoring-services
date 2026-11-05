import { useLocation } from 'react-router'

import type { JobService } from '@/app/api/wire'

import { keptInput, type KeptValues } from './keptInput'

/** The router state "Edit and resubmit" passes to a form: the job whose input fills it. */
export type EditState = { editJob: string }

export function editState(jobId: string): EditState {
  return { editJob: jobId }
}

function isEditState(state: unknown): state is EditState {
  return (
    typeof state === 'object' &&
    state !== null &&
    'editJob' in state &&
    typeof state.editJob === 'string'
  )
}

/**
 * On a form opened by "Edit and resubmit", the earlier job's input as typed; otherwise, or
 * when that input is no longer kept, none. The state isn't in the URL, so the address stays
 * the form's own.
 */
export function useEditedInput(service: JobService): KeptValues | undefined {
  const { state } = useLocation()
  return isEditState(state) ? keptInput(state.editJob, service) : undefined
}
