import type { components } from '@/app/api/schema'

// The one module that knows the API's field names. Everything else in the app
// reads the shapes below; if the API renames a field, only this file changes.

type Schemas = components['schemas']

/** A job as the API sends it: one member per service, tagged by `service`. */
export type WireJob = Schemas['ToolsJob'] | Schemas['CsnpJob']

/** The body of POST /jobs. Nothing in it needs renaming. */
export type JobRequest = Schemas['ToolsJobRequest'] | Schemas['CsnpJobRequest']

export type JobStatus = Schemas['JobStatus']
export type JobService = WireJob['service']
export type ToolsResult = Schemas['ToolsResult']
export type CsnpInput = Schemas['CsnpInput']
export type CsnpResult = Schemas['CsnpResult']
export type Problem = Schemas['Problem']
export type ValidationProblem = Schemas['ValidationProblem']
export type Versions = Schemas['Versions']

/** What every job has, whatever its service. Times are epoch milliseconds, null until reached. */
type JobBase = {
  id: string
  status: JobStatus
  createdAt: number
  startedAt: number | null
  finishedAt: number | null
  error: Problem | null
  versions: Versions
}

/** A job as the app uses it. Narrow by `service` to read its result. */
export type Job =
  | (JobBase & { service: 'tools'; result: ToolsResult | null })
  | (JobBase & { service: 'csnp'; result: CsnpResult | null })

// Epoch milliseconds rather than a Date: the store keeps only serializable values.
function toMillis(timestamp: string): number
function toMillis(timestamp: string | null): number | null
function toMillis(timestamp: string | null): number | null {
  return timestamp === null ? null : Date.parse(timestamp)
}

function fromWireBase(wire: WireJob): JobBase {
  return {
    id: wire.id,
    status: wire.status,
    createdAt: toMillis(wire.created_at),
    startedAt: toMillis(wire.started_at),
    finishedAt: toMillis(wire.finished_at),
    error: wire.error,
    versions: wire.versions,
  }
}

export function fromWireJob(wire: WireJob): Job {
  // One case per service, so each keeps its own result type.
  switch (wire.service) {
    case 'tools':
      return { ...fromWireBase(wire), service: wire.service, result: wire.result }
    case 'csnp':
      return { ...fromWireBase(wire), service: wire.service, result: wire.result }
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** Whether a response body is the API's 422 validation problem. */
export function isValidationProblem(value: unknown): value is ValidationProblem {
  return (
    isRecord(value) &&
    typeof value.status === 'number' &&
    Array.isArray(value.errors) &&
    value.errors.every(
      error => isRecord(error) && Array.isArray(error.loc) && typeof error.msg === 'string'
    )
  )
}

/** One of the API's messages about an input field; `item` is the list index it names, if any. */
export type InputError = { msg: string; item: number | null }

/**
 * A 422's errors, by the input field each names. The API's `loc` for an input field is
 * `["body", <service>, "input", <field>, ...]`, with a list item's index after the field.
 * An error on anything else, such as a field not in `fields`, goes in `other`.
 */
export function inputErrors<Field extends string>(
  problem: ValidationProblem,
  service: JobService,
  fields: readonly Field[]
): { fields: Partial<Record<Field, InputError[]>>; other: string[] } {
  const byField: Partial<Record<Field, InputError[]>> = {}
  const other: string[] = []
  for (const { loc, msg } of problem.errors) {
    const [body, tag, input, field, item] = loc
    const known = fields.find(name => name === field)
    if (body !== 'body' || tag !== service || input !== 'input' || known === undefined) {
      other.push(msg)
      continue
    }
    const error = { msg, item: typeof item === 'number' ? item : null }
    byField[known] = [...(byField[known] ?? []), error]
  }
  return { fields: byField, other }
}
