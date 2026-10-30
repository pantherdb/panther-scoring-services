import { http, HttpResponse, type AnyHandler } from 'msw'

import { jobNotFound } from '@/mocks/data/jobs'
import { versions } from '@/mocks/data/versions'
import { createJob, pollJob } from '@/mocks/jobs'

const PROBLEM = { 'Content-Type': 'application/problem+json' }

// Mock API handlers, shared by the dev server, the e2e build and Vitest.
export const handlers: AnyHandler[] = [
  http.get('/api/v1/versions', () => HttpResponse.json(versions)),

  http.post('/api/v1/jobs', async ({ request }) => {
    const body: unknown = await request.json()
    const isTools =
      typeof body === 'object' && body !== null && 'service' in body && body.service === 'tools'
    if (!isTools) {
      return HttpResponse.json(
        {
          type: 'about:blank',
          title: 'Unprocessable Content',
          status: 422,
          detail: 'The request is not valid.',
          errors: [
            { loc: ['body'], msg: 'Only the tools job is mocked', type: 'union_tag_invalid' },
          ],
        },
        { status: 422, headers: PROBLEM }
      )
    }
    const job = createJob()
    return HttpResponse.json(job, { status: 202, headers: { Location: `/api/v1/jobs/${job.id}` } })
  }),

  http.get('/api/v1/jobs/:id', ({ params }) => {
    const job = typeof params.id === 'string' ? pollJob(params.id) : undefined
    if (!job) return HttpResponse.json(jobNotFound, { status: 404, headers: PROBLEM })
    return HttpResponse.json(job)
  }),
]
