import { Badge, Loader } from '@mantine/core'

import type { Job, JobStatus as Status } from '@/app/api/wire'

import { isFinished } from './jobsApi'

const STATUS_LABELS: Record<Status, string> = {
  queued: 'Queued',
  running: 'Running',
  succeeded: 'Succeeded',
  failed: 'Failed',
}

type Props = {
  job: Job
}

// How long the job ran, from the API's own timestamps: no clock is read.
function runTime({ startedAt, finishedAt }: Job) {
  if (startedAt === null || finishedAt === null) return null
  return `${((finishedAt - startedAt) / 1000).toFixed(1)} s`
}

// The job's status, in a live region so a screen reader hears it change.
export function JobStatus({ job }: Props) {
  const ran = runTime(job)

  return (
    <div className="flex flex-col gap-1">
      <div role="status" className="flex items-center gap-2">
        <span className="font-medium">Status</span>
        <Badge variant="light">{STATUS_LABELS[job.status]}</Badge>
      </div>
      {!isFinished(job.status) && (
        <p className="flex items-center gap-2 text-sm text-ink-muted">
          <Loader size="xs" />
          This page updates by itself.
        </p>
      )}
      {ran !== null && <p className="text-sm text-ink-muted">Ran for {ran}</p>}
    </div>
  )
}
