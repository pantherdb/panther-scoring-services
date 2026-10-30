import type { Job } from '@/app/api/wire'

import { ToolsResult } from './ToolsResult'

type Props = {
  job: Job
}

// A succeeded job's result, in its service's form. A new service adds a case.
export function JobResult({ job }: Props) {
  if (job.result === null) return null
  switch (job.service) {
    case 'tools':
      return <ToolsResult result={job.result} />
  }
}
