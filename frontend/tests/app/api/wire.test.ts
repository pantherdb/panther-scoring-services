import { describe, expect, it } from 'vitest'

import { fromWireJob, type WireJob } from '@/app/api/wire'

const versions = {
  api: '0.1.0',
  engine: '0.1.0',
  tools: [
    { name: 'blastp', version: '2.17.0' },
    { name: 'epa-ng', version: null },
  ],
}

const succeeded: WireJob = {
  id: 'c56f34dc-cf36-429d-83d9-dcac03e46957',
  service: 'tools',
  status: 'succeeded',
  created_at: '2026-10-30T00:32:00.020522Z',
  started_at: '2026-10-30T00:32:00.021159Z',
  finished_at: '2026-10-30T00:32:01.540021Z',
  result: { tools: versions.tools },
  error: null,
  versions,
}

describe('fromWireJob', () => {
  it("renames the API's fields and turns its timestamps into epoch milliseconds", () => {
    expect(fromWireJob(succeeded)).toEqual({
      id: 'c56f34dc-cf36-429d-83d9-dcac03e46957',
      service: 'tools',
      status: 'succeeded',
      createdAt: Date.UTC(2026, 9, 30, 0, 32, 0, 20),
      startedAt: Date.UTC(2026, 9, 30, 0, 32, 0, 21),
      finishedAt: Date.UTC(2026, 9, 30, 0, 32, 1, 540),
      result: { tools: versions.tools },
      error: null,
      versions,
    })
  })

  it('keeps timestamps that are not reached yet as null', () => {
    const queued = fromWireJob({
      ...succeeded,
      status: 'queued',
      started_at: null,
      finished_at: null,
      result: null,
    })

    expect(queued.startedAt).toBeNull()
    expect(queued.finishedAt).toBeNull()
    expect(queued.createdAt).toBe(Date.UTC(2026, 9, 30, 0, 32, 0, 20))
  })

  it("passes a failed job's error through unchanged", () => {
    const error = {
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'The job failed.',
    }

    const failed = fromWireJob({ ...succeeded, status: 'failed', result: null, error })

    expect(failed.error).toEqual(error)
    expect(failed.result).toBeNull()
  })

  it('leaves no snake_case field in the result', () => {
    const keys = Object.keys(fromWireJob(succeeded))

    expect(keys.filter(key => key.includes('_'))).toEqual([])
  })
})
