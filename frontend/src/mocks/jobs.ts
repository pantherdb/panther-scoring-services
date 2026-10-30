import type { components } from '@/app/api/schema'
import { toolsJob } from '@/mocks/data/jobs'

type ToolsJob = components['schemas']['ToolsJob']

// The mocked API's jobs, by id, with how many times each has been polled. A job
// moves forward one status per poll: queued, then running, then succeeded.
const polls = new Map<string, number>()

const STATUS_BY_POLL = ['queued', 'running', 'succeeded'] as const

export function createJob(): ToolsJob {
  const id = crypto.randomUUID()
  polls.set(id, 0)
  return toolsJob(id, 'queued')
}

/** The job's next state, or undefined for an id no mocked job has. */
export function pollJob(id: string): ToolsJob | undefined {
  const count = polls.get(id)
  if (count === undefined) return undefined
  polls.set(id, count + 1)
  return toolsJob(id, STATUS_BY_POLL[Math.min(count, STATUS_BY_POLL.length - 1)])
}

/** Forgets every mocked job. Vitest calls it after each test. */
export function resetJobs() {
  polls.clear()
}
