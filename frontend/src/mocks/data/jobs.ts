import type { components } from '../../app/api/schema'
import { versions } from './versions'

// Mocked job bodies, as the API sends them. Also read by the @mock e2e spec, so
// keep to type imports and relative imports.

type ToolsJob = components['schemas']['ToolsJob']
type CsnpJob = components['schemas']['CsnpJob']
type CsnpResult = components['schemas']['CsnpResult']
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

// The times and error a job has in the given status.
function jobFields(id: string, status: JobStatus) {
  const started = status !== 'queued'
  const finished = status === 'succeeded' || status === 'failed'
  return {
    id,
    status,
    created_at: CREATED_AT,
    started_at: started ? STARTED_AT : null,
    finished_at: finished ? FINISHED_AT : null,
    error: status === 'failed' ? jobError : null,
    versions,
  }
}

/** A tools job in the given status, with the fields that status has. */
export function toolsJob(id: string, status: JobStatus): ToolsJob {
  return {
    ...jobFields(id, status),
    service: 'tools',
    result: status === 'succeeded' ? toolsResult : null,
  }
}

/**
 * MOCK DATA, not a score. The engine produced none of it: the ages, messages and pDel
 * values are made up to exercise the results table, and PTHR00000 is no PANTHER family.
 * The substitutions are the example input's, so the mocked flow reads naturally.
 */
export const csnpResult: CsnpResult = {
  family: 'PTHR00000',
  scores: [
    { substitution: 'L46P', age: 400, message: 'probably damaging', pdel: '0.80' },
    { substitution: 'C130R', age: 300, message: 'possibly damaging', pdel: '0.50' },
    { substitution: 'R163C', age: 100, message: 'probably benign', pdel: '0.20' },
    {
      substitution: 'R176C',
      age: null,
      message: 'Not scored: Invalid substitution',
      pdel: null,
    },
  ],
}

/** A csnp job in the given status, with the mock result once it has succeeded. */
export function csnpJob(id: string, status: JobStatus): CsnpJob {
  return {
    ...jobFields(id, status),
    service: 'csnp',
    result: status === 'succeeded' ? csnpResult : null,
  }
}

/** The API's answer to a valid csnp request until scoring is ported: 501, and no job. */
export const csnpUnavailable: Problem = {
  type: 'about:blank',
  title: 'Not Implemented',
  status: 501,
  detail: "cSNP scoring isn't available yet.",
}
