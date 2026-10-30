import { http, HttpResponse, type AnyHandler } from 'msw'

import { versions } from '@/mocks/data/versions'

// Mock API handlers, shared by the dev server, the e2e build and Vitest.
export const handlers: AnyHandler[] = [
  http.get('/api/v1/versions', () => HttpResponse.json(versions)),
]
