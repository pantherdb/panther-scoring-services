import type { components } from '@/app/api/schema'
import { csnpJob, refmapJob, toolsJob } from '@/mocks/data/jobs'

type WireJob =
  | components['schemas']['ToolsJob']
  | components['schemas']['CsnpJob']
  | components['schemas']['RefmapJob']
type Service = WireJob['service']
type JobStatus = components['schemas']['JobStatus']

// Each service's job body. A refmap job maps the IDs it was submitted with.
const JOB_BODIES: Record<
  Service,
  (id: string, status: JobStatus, ids: readonly string[]) => WireJob
> = {
  tools: toolsJob,
  csnp: csnpJob,
  refmap: refmapJob,
}

// The mocked API's jobs, by id, with their service, the IDs a refmap job was submitted with,
// and how many times each has been polled. A job moves forward one status per poll: queued,
// then running, then succeeded.
const jobs = new Map<string, { service: Service; ids: readonly string[]; polls: number }>()

const STATUS_BY_POLL = ['queued', 'running', 'succeeded'] as const

/** A new queued job. `ids` are what a refmap job maps; other services ignore them. */
export function createJob(service: Service = 'tools', ids: readonly string[] = []): WireJob {
  const id = crypto.randomUUID()
  jobs.set(id, { service, ids, polls: 0 })
  return JOB_BODIES[service](id, 'queued', ids)
}

/** The job's next state, or undefined for an id no mocked job has. */
export function pollJob(id: string): WireJob | undefined {
  const job = jobs.get(id)
  if (job === undefined) return undefined
  const { service, ids, polls } = job
  jobs.set(id, { service, ids, polls: polls + 1 })
  return JOB_BODIES[service](id, STATUS_BY_POLL[Math.min(polls, STATUS_BY_POLL.length - 1)], ids)
}

/** Forgets every mocked job. Vitest calls it after each test. */
export function resetJobs() {
  jobs.clear()
}
