import { Alert } from '@mantine/core'

import type { Job, JobService } from '@/app/api/wire'
import { VersionList } from '@/components/VersionList'

import { isFinished } from './jobsApi'
import { JobResult } from './JobResult'
import { JobStatus } from './JobStatus'

// Each service's job page heading. A new service adds a row.
const SERVICE_TITLES: Record<JobService, string> = {
  tools: 'Scoring tools check',
  csnp: 'Coding SNP impact scoring',
}

type Props = {
  job: Job
}

// A job: its status, then, once it has finished, its outcome and the versions it ran with.
export function JobDetails({ job }: Props) {
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{SERVICE_TITLES[job.service]}</h2>
        <JobStatus job={job} />
      </div>

      {job.status === 'succeeded' && <JobResult job={job} />}

      {job.status === 'failed' && (
        <Alert title="The job failed">{job.error?.detail ?? 'No reason was given.'}</Alert>
      )}

      {isFinished(job.status) && (
        <section className="flex flex-col gap-2">
          <h3 className="font-semibold">Versions used</h3>
          <div className="text-sm">
            <VersionList versions={job.versions} />
          </div>
        </section>
      )}
    </section>
  )
}
