import type { components } from '../../app/api/schema'
import { versions } from './versions'

// Mocked job bodies, as the API sends them. Also read by the @mock e2e spec, so
// keep to type imports and relative imports.

type ToolsJob = components['schemas']['ToolsJob']
type JobStatus = components['schemas']['JobStatus']
type Problem = components['schemas']['Problem']

/** The tools job's result: each tool the versions mock reports. */
export const toolsResult: components['schemas']['ToolsResult'] = { tools: versions.tools }

/** A failed job's error, generic as the API makes it. */
export const jobError: Problem = {
  type: 'about:blank',
  title: 'Internal Server Error',
  status: 500,
  detail: 'The job hit an unexpected error and could not complete.',
}

/** The API's answer to an unknown, malformed or expired job id. */
export const jobNotFound: Problem = {
  type: 'about:blank',
  title: 'Not Found',
  status: 404,
  detail: 'There is no job with this id. A finished job expires after a time.',
}

// Fixed times, so the run time shown is predictable: the job runs for 1.5 s.
const CREATED_AT = '2026-10-29T12:00:00.000Z'
const STARTED_AT = '2026-10-29T12:00:00.020Z'
const FINISHED_AT = '2026-10-29T12:00:01.520Z'

/** A tools job in the given status, with the fields that status has. */
export function toolsJob(id: string, status: JobStatus): ToolsJob {
  const started = status !== 'queued'
  const finished = status === 'succeeded' || status === 'failed'
  return {
    id,
    service: 'tools',
    status,
    created_at: CREATED_AT,
    started_at: started ? STARTED_AT : null,
    finished_at: finished ? FINISHED_AT : null,
    result: status === 'succeeded' ? toolsResult : null,
    error: status === 'failed' ? jobError : null,
    versions,
  }
}
