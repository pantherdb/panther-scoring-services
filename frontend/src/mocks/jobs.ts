import type { components } from '@/app/api/schema'
import { csnpJob, toolsJob } from '@/mocks/data/jobs'

type WireJob = components['schemas']['ToolsJob'] | components['schemas']['CsnpJob']
type Service = WireJob['service']
type JobStatus = components['schemas']['JobStatus']

const JOB_BODIES: Record<Service, (id: string, status: JobStatus) => WireJob> = {
  tools: toolsJob,
  csnp: csnpJob,
}

// The mocked API's jobs, by id, with their service and how many times each has been
// polled. A job moves forward one status per poll: queued, then running, then succeeded.
const jobs = new Map<string, { service: Service; polls: number }>()

const STATUS_BY_POLL = ['queued', 'running', 'succeeded'] as const

export function createJob(service: Service = 'tools'): WireJob {
  const id = crypto.randomUUID()
  jobs.set(id, { service, polls: 0 })
  return JOB_BODIES[service](id, 'queued')
}

/** The job's next state, or undefined for an id no mocked job has. */
export function pollJob(id: string): WireJob | undefined {
  const job = jobs.get(id)
  if (job === undefined) return undefined
  const { service, polls } = job
  jobs.set(id, { service, polls: polls + 1 })
  return JOB_BODIES[service](id, STATUS_BY_POLL[Math.min(polls, STATUS_BY_POLL.length - 1)])
}

/** Forgets every mocked job. Vitest calls it after each test. */
export function resetJobs() {
  jobs.clear()
}
