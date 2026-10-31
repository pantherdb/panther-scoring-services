import { http, HttpResponse, type AnyHandler } from 'msw'

import { jobNotFound } from '@/mocks/data/jobs'
import { species } from '@/mocks/data/species'
import { versions } from '@/mocks/data/versions'
import { createJob, pollJob } from '@/mocks/jobs'

const PROBLEM = { 'Content-Type': 'application/problem+json' }

// A refmap request's `input.ids`, or none when the body has no list of strings there.
function submittedIds(body: unknown): string[] {
  if (typeof body !== 'object' || body === null || !('input' in body)) return []
  const { input } = body
  if (typeof input !== 'object' || input === null || !('ids' in input)) return []
  const { ids } = input
  return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === 'string') : []
}

// Mock API handlers, shared by the dev server, the e2e build and Vitest.
export const handlers: AnyHandler[] = [
  http.get('/api/v1/versions', () => HttpResponse.json(versions)),

  http.get('/api/v1/csnp/species', () => HttpResponse.json(species)),

  http.post('/api/v1/jobs', async ({ request }) => {
    const body: unknown = await request.json()
    const service =
      typeof body === 'object' && body !== null && 'service' in body ? body.service : undefined
    // A csnp or refmap job is accepted as the API accepts it, and gets a mock result: a refmap
    // job maps the IDs it was sent. No input is validated, and refmap gets no 501.
    if (service !== 'tools' && service !== 'csnp' && service !== 'refmap') {
      return HttpResponse.json(
        {
          type: 'about:blank',
          title: 'Unprocessable Content',
          status: 422,
          detail: 'The request is not valid.',
          errors: [
            {
              loc: ['body'],
              msg: 'Only tools, csnp and refmap jobs are mocked',
              type: 'union_tag_invalid',
            },
          ],
        },
        { status: 422, headers: PROBLEM }
      )
    }
    const job = createJob(service, submittedIds(body))
    return HttpResponse.json(job, { status: 202, headers: { Location: `/api/v1/jobs/${job.id}` } })
  }),

  http.get('/api/v1/jobs/:id', ({ params }) => {
    const job = typeof params.id === 'string' ? pollJob(params.id) : undefined
    if (!job) return HttpResponse.json(jobNotFound, { status: 404, headers: PROBLEM })
    return HttpResponse.json(job)
  }),
]
