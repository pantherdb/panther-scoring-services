import { Button } from '@mantine/core'
import { Link } from 'react-router'

import type { Job, JobService } from '@/app/api/wire'

import { keptInput } from './keptInput'
import { editState } from './useEditedInput'

// Where each service's job page leads next: an empty form, or home for the tools check. A new
// service adds a row.
const NEXT: Record<JobService, { label: string; path: string }> = {
  tools: { label: 'Back to home', path: '/' },
  csnp: { label: 'New cSNP search', path: '/csnp' },
  refmap: { label: 'New ID mapping', path: '/refmap' },
}

type Props = {
  job: Job
}

// Shown whatever the job's status, so another job can start while this one runs.
export function JobNextSteps({ job }: Props) {
  const next = NEXT[job.service]
  const editable = job.service !== 'tools' && keptInput(job.id, job.service) !== undefined
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
