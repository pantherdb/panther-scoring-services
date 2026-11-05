import { Button } from '@mantine/core'
import { Link } from 'react-router'

import type { Job, JobService } from '@/app/api/wire'
import { service } from '@/app/services'

import { isEditable, keptInput } from './keptInput'
import { editState } from './useEditedInput'

// Where each service's job page leads next: its empty form, from services.ts, or home for the
// tools check. A new service adds a row.
const NEXT: Record<JobService, { label: string; path: string }> = {
  tools: { label: 'Back to home', path: '/' },
  csnp: { label: 'New cSNP search', path: service('csnp').path },
  refmap: { label: 'New ID mapping', path: service('refmap').path },
}

type Props = {
  job: Job
}

// Shown whatever the job's status, so another job can start while this one runs.
export function JobNextSteps({ job }: Props) {
  const next = NEXT[job.service]
  // The same check the form makes, so the button never opens an empty form.
  const editable = isEditable(job.service) && keptInput(job.id, job.service) !== undefined
  return (
    <div className="flex flex-wrap gap-2">
      <Button component={Link} to={next.path} variant="default">
        {next.label}
      </Button>
      {editable && (
        <Button component={Link} to={next.path} state={editState(job.id)} variant="default">
          Edit and resubmit
        </Button>
      )}
    </div>
  )
}
