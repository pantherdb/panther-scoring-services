import type { components } from '@/app/api/schema'
import { csnpJob, refmapJob, toolsJob } from '@/mocks/data/jobs'

type WireJob =
  | components['schemas']['ToolsJob']
  | components['schemas']['CsnpJob']
  | components['schemas']['RefmapJob']
type Service = WireJob['service']
type JobStatus = components['schemas']['JobStatus']

/** What a refmap job was submitted with; other services ignore it. */
type RefmapRequest = { ids: readonly string[]; organism: string }

// Each service's job body. A refmap job maps the IDs it was submitted with, against its organism.
const JOB_BODIES: Record<
  Service,
  (id: string, status: JobStatus, request: RefmapRequest) => WireJob
> = {
  tools: toolsJob,
  csnp: csnpJob,
  refmap: (id, status, { ids, organism }) => refmapJob(id, status, ids, organism),
}

// The mocked API's jobs, by id, with their service, what a refmap job was submitted with, and
// how many times each has been polled. A job moves forward one status per poll: queued, then
// running, then succeeded.
const jobs = new Map<string, { service: Service; request: RefmapRequest; polls: number }>()

const STATUS_BY_POLL = ['queued', 'running', 'succeeded'] as const

/**
 * A new queued job. `ids` and `organism` are what a refmap job maps, against ENDPU unless
 * given; other services ignore them.
 */
export function createJob(
  service: Service = 'tools',
  ids: readonly string[] = [],
  organism = 'ENDPU'
): WireJob {
  const id = crypto.randomUUID()
  const request = { ids, organism }
  jobs.set(id, { service, request, polls: 0 })
  return JOB_BODIES[service](id, 'queued', request)
}

/** The job's next state, or undefined for an id no mocked job has. */
export function pollJob(id: string): WireJob | undefined {
  const job = jobs.get(id)
  if (job === undefined) return undefined
  const { service, request, polls } = job
  jobs.set(id, { service, request, polls: polls + 1 })
  return JOB_BODIES[service](
    id,
    STATUS_BY_POLL[Math.min(polls, STATUS_BY_POLL.length - 1)],
    request
  )
}

/** Forgets every mocked job. Vitest calls it after each test. */
export function resetJobs() {
  jobs.clear()
}
