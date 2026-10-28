import type { AnyHandler } from 'msw'

// Mock API handlers, shared by the dev server, the e2e build and Vitest.
export const handlers: AnyHandler[] = []
