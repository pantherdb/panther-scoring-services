import type { Job } from '@/app/api/wire'

import { CsnpScores } from './CsnpScores'
import { RefmapMappings } from './RefmapMappings'
import { ToolsResult } from './ToolsResult'

type Props = {
  job: Job
}

// A succeeded job's result, in its service's form. A new service adds a case.
export function JobResult({ job }: Props) {
  switch (job.service) {
    case 'tools':
      return job.result && <ToolsResult result={job.result} />
    case 'csnp':
      return job.result && <CsnpScores result={job.result} />
    case 'refmap':
      return job.result && <RefmapMappings jobId={job.id} result={job.result} />
  }
}
