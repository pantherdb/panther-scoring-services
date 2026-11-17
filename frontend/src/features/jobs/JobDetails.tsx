import { Alert } from '@mantine/core'

import type { Job, JobService } from '@/app/api/wire'
import { service } from '@/app/services'
import { VersionList } from '@/components/VersionList'

import { JobNextSteps } from './JobNextSteps'
import { isFinished } from './jobsApi'
import { JobResult } from './JobResult'
import { JobStatus } from './JobStatus'

// A job page's heading: its service's title from services.ts, or the tools check's own, since
// the tools check isn't a service there.
function titleOf(jobService: JobService) {
  return jobService === 'tools' ? 'Scoring tools check' : service(jobService).title
}

type Props = {
  job: Job
}

// A job: its status and the next step, then, once it has finished, its outcome and the versions it ran with.
export function JobDetails({ job }: Props) {
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{titleOf(job.service)}</h2>
        <JobStatus job={job} />
      </div>

      <JobNextSteps job={job} />

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
