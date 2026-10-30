import type { components } from '@/app/api/schema'

// The one module that knows the API's field names. Everything else in the app
// reads the shapes below; if the API renames a field, only this file changes.

type Schemas = components['schemas']

/** A job as the API sends it. Becomes a union when a second service is added. */
export type WireJob = Schemas['ToolsJob']

/** The body of POST /jobs. Nothing in it needs renaming. */
export type JobRequest = Schemas['ToolsJobRequest']

export type JobStatus = Schemas['JobStatus']
export type JobService = WireJob['service']
export type ToolsResult = Schemas['ToolsResult']
export type Problem = Schemas['Problem']
export type Versions = Schemas['Versions']

/** A job as the app uses it. Times are epoch milliseconds, null until reached. */
export type Job = {
  id: string
  service: JobService
  status: JobStatus
  createdAt: number
  startedAt: number | null
  finishedAt: number | null
  result: ToolsResult | null
  error: Problem | null
  versions: Versions
}

// Epoch milliseconds rather than a Date: the store keeps only serializable values.
function toMillis(timestamp: string): number
function toMillis(timestamp: string | null): number | null
function toMillis(timestamp: string | null): number | null {
  return timestamp === null ? null : Date.parse(timestamp)
}

export function fromWireJob(wire: WireJob): Job {
  return {
    id: wire.id,
    service: wire.service,
    status: wire.status,
    createdAt: toMillis(wire.created_at),
    startedAt: toMillis(wire.started_at),
    finishedAt: toMillis(wire.finished_at),
    result: wire.result,
    error: wire.error,
    versions: wire.versions,
  }
}
