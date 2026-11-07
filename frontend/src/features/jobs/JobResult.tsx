import type { Job } from '@/app/api/wire'

import { CsnpScores } from './CsnpScores'
import { RefmapMappings } from './RefmapMappings'
import { ToolsResult } from './ToolsResult'
import { useOrganismLabel } from './useOrganismLabel'

type Props = {
  job: Job
}

// A succeeded job's result, in its service's form. A new service adds a case. The organism list
// is fetched here, not in the result's component, and only for a refmap job.
export function JobResult({ job }: Props) {
  const organism = useOrganismLabel(
    job.service === 'refmap' && job.result ? job.result.organism : null
  )
  switch (job.service) {
    case 'tools':
      return job.result && <ToolsResult result={job.result} />
    case 'csnp':
      return job.result && <CsnpScores result={job.result} />
    case 'refmap':
      return (
        job.result && (
          <RefmapMappings
            jobId={job.id}
            result={job.result}
            organism={organism ?? job.result.organism}
          />
        )
      )
  }
}
